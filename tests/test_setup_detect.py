"""Noninteractive setup asset selection and platform guards."""

import threading
from unittest.mock import patch

import pytest

from vigil_ui import setup_service


def test_detect_backend_prefers_rocm_on_amd_host():
    def which(name):
        return "/opt/rocm/bin/rocminfo" if name == "rocminfo" else None

    with patch.object(setup_service.shutil, "which", side_effect=which):
        assert setup_service.detect_backend() == "rocm"


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
