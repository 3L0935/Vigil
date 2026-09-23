"""Noninteractive setup asset selection and platform guards."""

import io
import json
import tarfile
import threading
from unittest.mock import patch

import pytest

from vigil_ui import setup_service


def test_detect_backend_prefers_rocm_on_amd_host():
    def which(name):
        return "/opt/rocm/bin/rocminfo" if name == "rocminfo" else None

    with patch.object(setup_service.shutil, "which", side_effect=which):
        assert setup_service.detect_backend() == "rocm"


def test_detect_backend_uses_vulkan_for_older_rocm_runtime():
    def which(name):
        return "/usr/bin/" + name if name in ("rocminfo", "vulkaninfo") else None

    with patch.object(setup_service.shutil, "which", side_effect=which), \
         patch.object(setup_service, "_local_rocm_major", return_value=7):
        assert setup_service.detect_backend() == "vulkan"


@pytest.mark.parametrize("vram, expected", [
    (0, "Qwen_Qwen3.5-0.8B-Q4_K_M.gguf"),
    (8192, "Qwen_Qwen3.5-4B-Q4_K_M.gguf"),
    (20480, "Qwen_Qwen3.5-9B-Q8_0.gguf"),
])
def test_recommended_model_respects_vram_budget(vram, expected):
    with patch.object(setup_service, "detect_vram_mb", return_value=vram):
        assert setup_service.recommended_model() == expected


def test_unsupported_platform_rejects_linux_binary_catalog():
    with patch.object(setup_service.platform, "system", return_value="Windows"):
        with pytest.raises(RuntimeError, match="Linux x86_64"):
            setup_service.fetch_binary_asset("rocm")


def test_binary_catalog_skips_latest_release_without_binaries(monkeypatch):
    releases = [
        {"assets": [{"name": "nightly-tag.txt", "browser_download_url": "https://example.invalid/tag"}]},
        {"assets": []},
        {"assets": [{"name": "llama-b123-bin-ubuntu-rocm-10.0-x64.tar.gz",
                      "browser_download_url": "https://example.invalid/rocm.tar.gz"}]},
    ]
    payload = json.dumps(releases).encode()
    monkeypatch.setattr(setup_service.urllib.request, "urlopen",
                        lambda *args, **kwargs: io.BytesIO(payload))
    monkeypatch.setattr(setup_service, "_local_rocm_major", lambda: 10)
    with patch.object(setup_service.platform, "system", return_value="Linux"), \
         patch.object(setup_service.platform, "machine", return_value="x86_64"):
        assert setup_service.fetch_binary_asset("rocm") == (
            "https://example.invalid/rocm.tar.gz",
            "llama-b123-bin-ubuntu-rocm-10.0-x64.tar.gz",
        )


def test_binary_catalog_rejects_different_rocm_major(monkeypatch):
    releases = [{"assets": [{"name": "llama-b123-bin-ubuntu-rocm-10.0-x64.tar.gz",
                            "browser_download_url": "https://example.invalid/rocm.tar.gz"}]}]
    monkeypatch.setattr(setup_service.urllib.request, "urlopen",
                        lambda *args, **kwargs: io.BytesIO(json.dumps(releases).encode()))
    monkeypatch.setattr(setup_service, "_local_rocm_major", lambda: 7)
    with patch.object(setup_service.platform, "system", return_value="Linux"), \
         patch.object(setup_service.platform, "machine", return_value="x86_64"):
        with pytest.raises(RuntimeError, match="No llama-server build found for rocm"):
            setup_service.fetch_binary_asset("rocm")


def test_binary_download_reports_received_bytes(monkeypatch, tmp_path):
    def retrieve(url, path, reporthook=None):
        from pathlib import Path
        Path(path).write_bytes(b"payload")
        reporthook(1, 4, 8)
        reporthook(2, 4, 8)

    monkeypatch.setattr(setup_service.urllib.request, "urlretrieve", retrieve)
    received = []
    path = setup_service._download_to_temp("https://example.invalid/asset", tmp_path,
                                           ".zip", lambda done, total: received.append((done, total)))
    assert path.read_bytes() == b"payload"
    assert received == [(4, 8), (8, 8)]


def test_model_download_reports_hub_progress(monkeypatch, tmp_path):
    import huggingface_hub

    cached = tmp_path / "cached.gguf"
    cached.write_bytes(b"model")
    monkeypatch.setattr(setup_service, "MODEL_DIR", tmp_path / "vigil-models")

    def fake_download(*, tqdm_class, **kwargs):
        with tqdm_class(total=100, disable=True) as bar:
            bar.update(50)
            bar.update(50)
        return str(cached)

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", fake_download)
    received = []
    result = setup_service.install_model("Qwen_Qwen3.5-9B-Q4_K_M.gguf", threading.Event(),
                                         lambda done, total: received.append((done, total)))
    assert result.is_file()
    assert (50, 100) in received
    assert (100, 100) in received


def test_binary_install_preserves_shared_library_links(monkeypatch, tmp_path):
    archive = tmp_path / "release.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        for name, data in (("release/llama-server", b"binary"),
                           ("release/libcommon.so.1", b"library")):
            item = tarfile.TarInfo(name)
            item.size = len(data)
            bundle.addfile(item, io.BytesIO(data))
        link = tarfile.TarInfo("release/libcommon.so")
        link.type = tarfile.SYMTYPE
        link.linkname = "libcommon.so.1"
        bundle.addfile(link)

    target = tmp_path / "vigil-llama"
    target.mkdir()
    monkeypatch.setattr(setup_service, "LLAMA_DIR", target)
    monkeypatch.setattr(setup_service, "fetch_binary_asset",
                        lambda backend: ("https://example.invalid/release", "release.tar.gz"))
    monkeypatch.setattr(setup_service, "_download_to_temp",
                        lambda *args, **kwargs: archive)
    monkeypatch.setattr(setup_service, "_binary_runs", lambda path: True)
    binary = setup_service.install_binary("vulkan", threading.Event())
    assert binary.read_bytes() == b"binary"
    assert (target / "libcommon.so").is_symlink()
    assert (target / "libcommon.so").read_bytes() == b"library"
    assert (target / "backend.txt").read_text() == "vulkan"
