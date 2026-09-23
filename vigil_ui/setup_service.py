"""Noninteractive first-run preparation used by the Fold wizard."""

import fnmatch
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile

from .assets import download_voice, is_loopback_url, url_is_valid
from data_paths import DATA_DIR


MODEL_DIR = DATA_DIR / "models"
LLAMA_DIR = DATA_DIR / "llama"
RELEASE_API = "https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=20"
MODEL_TIERS = (
    ("Qwen3.5 0.8B Q4", "bartowski/Qwen_Qwen3.5-0.8B-GGUF", "Qwen_Qwen3.5-0.8B-Q4_K_M.gguf", 650),
    ("Qwen3.5 2B Q4", "bartowski/Qwen_Qwen3.5-2B-GGUF", "Qwen_Qwen3.5-2B-Q4_K_M.gguf", 1500),
    ("LFM2.5 2.6B Q4", "LiquidAI/LFM2.5-2.6B-GGUF", "LFM2.5-2.6B-Q4_K_M.gguf", 2500),
    ("Ministral 3B Q4", "bartowski/mistralai_Ministral-3-3B-Instruct-2512-GGUF", "mistralai_Ministral-3-3B-Instruct-2512-Q4_K_M.gguf", 2000),
    ("Qwen3.5 4B Q4", "bartowski/Qwen_Qwen3.5-4B-GGUF", "Qwen_Qwen3.5-4B-Q4_K_M.gguf", 2500),
    ("Qwen3.5 9B Q4", "bartowski/Qwen_Qwen3.5-9B-GGUF", "Qwen_Qwen3.5-9B-Q4_K_M.gguf", 5500),
    ("Qwen3.5 9B Q8", "bartowski/Qwen_Qwen3.5-9B-GGUF", "Qwen_Qwen3.5-9B-Q8_0.gguf", 10000),
    ("Mistral Small 3.2 24B Q4", "bartowski/mistralai_Mistral-Small-3.2-24B-Instruct-2506-GGUF", "mistralai_Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf", 13000),
)
BINARY_PATTERNS = {
    "cpu": "llama-*-bin-ubuntu-x64.*",
    "rocm": "llama-*-bin-ubuntu-rocm-*-x64.*",
    "vulkan": "llama-*-bin-ubuntu-vulkan-x64.*",
    "cuda": "llama-*-bin-ubuntu-x64.*",
}


class SetupCancelled(RuntimeError):
    pass


def detect_backend() -> str:
    if shutil.which("rocm-smi") or shutil.which("rocminfo"):
        # Current upstream Linux binaries target ROCm 10. Older local runtimes
        # can use the Vulkan GPU build without a mismatched HIP runtime.
        major = _local_rocm_major()
        if major is not None and major < 10 and shutil.which("vulkaninfo"):
            return "vulkan"
        return "rocm"
    if shutil.which("nvidia-smi"):
        return "cuda"
    if shutil.which("vulkaninfo"):
        return "vulkan"
    return "cpu"


def detect_vram_mb() -> int:
    if platform.system() == "Linux":
        for path in Path("/sys/class/drm").glob("*/device/mem_info_vram_total"):
            try:
                amount = int(path.read_text().strip()) // (1024 * 1024)
                if amount > 0:
                    return amount
            except (OSError, ValueError):
                pass
    return 0


def recommended_model() -> str:
    budget = int(detect_vram_mb() * 0.55)
    eligible = [tier for tier in MODEL_TIERS if tier[3] <= budget]
    return (eligible[-1] if eligible else MODEL_TIERS[0])[2]


def _local_rocm_major() -> int | None:
    executable = shutil.which("rocminfo") or shutil.which("rocm-smi")
    if not executable:
        return None
    version_file = Path(executable).resolve().parent.parent / ".info" / "version"
    try:
        match = re.match(r"(\d+)", version_file.read_text().strip())
        return int(match.group(1)) if match else None
    except OSError:
        return None


def fetch_binary_asset(backend: str) -> tuple[str, str]:
    if platform.system() != "Linux" or platform.machine().lower() not in ("x86_64", "amd64"):
        raise RuntimeError("Automatic llama-server download is available only for Linux x86_64. Choose an existing binary.")
    if backend not in BINARY_PATTERNS:
        raise ValueError("Unsupported backend")
    local_rocm_major = _local_rocm_major() if backend == "rocm" else None
    with urllib.request.urlopen(RELEASE_API, timeout=20) as response:
        releases = json.load(response)
    for release in releases:
        for asset in release.get("assets", []):
            name = asset["name"]
            if not fnmatch.fnmatch(name, BINARY_PATTERNS[backend]):
                continue
            if not name.endswith((".zip", ".tar.gz")):
                continue
            if backend == "cpu" and ("rocm" in name.lower() or "vulkan" in name.lower()):
                continue
            if backend == "rocm":
                asset_version = re.search(r"-rocm-(\d+)\.", name)
                if (local_rocm_major is not None and asset_version
                        and int(asset_version.group(1)) != local_rocm_major):
                    continue
            return asset["browser_download_url"], name
    raise RuntimeError("No llama-server build found for " + backend)


def _download_to_temp(url: str, directory: Path, suffix: str, progress=None) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=directory, suffix=suffix, delete=False) as tmp:
        path = Path(tmp.name)
    try:
        hook = None
        if progress is not None:
            hook = lambda blocks, size, total: progress(
                min(blocks * size, total) if total > 0 else blocks * size,
                max(total, 0),
            )
        urllib.request.urlretrieve(url, path, reporthook=hook)
        if not path.stat().st_size:
            raise RuntimeError("Empty download")
        return path
    except Exception:
        path.unlink(missing_ok=True)
        raise


def install_binary(backend: str, cancelled, progress=None) -> Path:
    existing = LLAMA_DIR / "llama-server"
    marker = LLAMA_DIR / "backend.txt"
    if (existing.is_file() and existing.stat().st_size and marker.is_file()
            and marker.read_text().strip() == backend and _binary_runs(existing)):
        return existing
    url, name = fetch_binary_asset(backend)
    archive = _download_to_temp(url, LLAMA_DIR, ".zip" if name.endswith(".zip") else ".tar.gz", progress)
    stage = Path(tempfile.mkdtemp(dir=LLAMA_DIR, prefix="stage-"))
    try:
        if cancelled.is_set():
            raise SetupCancelled()
        if name.endswith(".zip"):
            with zipfile.ZipFile(archive) as bundle:
                entries = ((item.filename, bundle.read(item)) for item in bundle.infolist()
                           if not item.is_dir() and _binary_entry(item.filename))
                _write_binary_entries(entries, stage)
        else:
            with tarfile.open(archive) as bundle:
                members = bundle.getmembers()
                entries = ((item.name, bundle.extractfile(item).read()) for item in members
                           if item.isfile() and _binary_entry(item.name))
                _write_binary_entries(entries, stage)
                _write_binary_links(((item.name, item.linkname) for item in members
                                     if item.issym() and _binary_entry(item.name)), stage)
        binary = stage / "llama-server"
        if not binary.is_file() or not binary.stat().st_size:
            raise RuntimeError("llama-server is missing from the archive")
        if not _binary_runs(binary):
            raise RuntimeError("Downloaded llama-server could not start")
        (stage / "backend.txt").write_text(backend)
        for item in sorted(stage.iterdir(), key=lambda path: (path.name == "backend.txt",
                                                       path.name == "llama-server")):
            if cancelled.is_set():
                raise SetupCancelled()
            os.replace(item, LLAMA_DIR / item.name)
        return existing
    finally:
        archive.unlink(missing_ok=True)
        shutil.rmtree(stage, ignore_errors=True)


def _write_binary_entries(entries, stage: Path) -> None:
    for original, data in entries:
        name = Path(original).name
        target = stage / name
        target.write_bytes(data)
        target.chmod(0o755)


def _write_binary_links(links, stage: Path) -> None:
    links = list(links)
    available = {path.name for path in stage.iterdir()} | {Path(name).name for name, _ in links}
    for original, linked in links:
        name = Path(original).name
        target = Path(linked).name
        if linked != target or target not in available or name == target:
            continue
        (stage / name).symlink_to(target)


def _binary_runs(binary: Path) -> bool:
    try:
        result = subprocess.run([str(binary), "--version"], capture_output=True, timeout=15)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _binary_entry(path: str) -> bool:
    name = Path(path).name
    return name in ("llama-server", "llama-server.exe") or name.endswith(".dylib") or ".so" in name


def install_model(choice: str, cancelled, progress=None) -> Path:
    path = Path(choice).expanduser()
    if path.is_file() and path.suffix == ".gguf" and path.stat().st_size:
        return path
    tier = next((tier for tier in MODEL_TIERS if tier[2] == choice), None)
    if tier is None:
        raise ValueError("Choose a GGUF file or a catalog model")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    target = MODEL_DIR / tier[2]
    if target.is_file() and target.stat().st_size:
        return target
    if cancelled.is_set():
        raise SetupCancelled()
    from huggingface_hub import hf_hub_download
    kwargs = {}
    if progress is not None:
        from tqdm.auto import tqdm

        class DownloadProgress(tqdm):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._received = int(kwargs.get("initial") or 0)

            def update(self, amount=1):
                result = super().update(amount)
                self._received += amount
                progress(int(self._received), int(self.total or 0))
                return result

        kwargs["tqdm_class"] = DownloadProgress
    cached = Path(hf_hub_download(repo_id=tier[1], filename=tier[2], **kwargs))
    if cancelled.is_set():
        raise SetupCancelled()
    with tempfile.NamedTemporaryFile(dir=MODEL_DIR, prefix="model-", delete=False) as tmp:
        partial = Path(tmp.name)
    try:
        shutil.copyfile(cached, partial)
        if not partial.stat().st_size:
            raise RuntimeError("Empty model download")
        os.replace(partial, target)
    finally:
        partial.unlink(missing_ok=True)
    return target


def prepare(draft: dict[str, str], cancelled, report, progress=None) -> dict[str, str]:
    """Prepare assets and return DB values; caller commits after success."""
    values = dict(draft)
    if values["hotkey_dict"].strip() == values["hotkey_assist"].strip():
        raise ValueError("Dictation and assistant shortcuts must differ")
    provider = values["llm_provider"]
    if provider == "llama_cpp":
        endpoint = values.get("llama_server_url", "http://localhost:8081")
        if not url_is_valid(endpoint):
            raise ValueError("Invalid llama-server endpoint")
        if values.get("local_only", "true") == "true" and not is_loopback_url(endpoint):
            raise ValueError("Remote inference is blocked by local mode")
        report("binary")
        existing_binary = values.get("use_existing_binary", "true" if values.get("llama_server_bin") else "false") == "true"
        binary = Path(values.get("llama_server_bin", "")).expanduser()
        if existing_binary:
            if not binary.is_file() or not binary.stat().st_size or not os.access(binary, os.X_OK):
                raise ValueError("Selected llama-server binary is not executable")
        else:
            binary = install_binary(values.get("llama_backend", detect_backend()), cancelled,
                                    progress=(lambda done, total: progress("binary", done, total)) if progress else None)
            values["llama_server_managed"] = "true"
        if existing_binary:
            values["llama_server_managed"] = values.get("llama_server_managed", "false")
        values["llama_server_bin"] = str(binary)
        report("model")
        model_choice = (values["llama_model"] if values.get("use_existing_model", "true") == "true"
                        else values.get("llama_catalog_model", recommended_model()))
        values["llama_model"] = str(install_model(model_choice, cancelled,
                                    progress=(lambda done, total: progress("model", done, total)) if progress else None))
    elif provider in ("ollama_local", "ollama_cloud"):
        url_key = "ollama_local_url" if provider == "ollama_local" else "ollama_cloud_url"
        if not url_is_valid(values[url_key]):
            raise ValueError("Invalid Ollama endpoint")
        if values["local_only"] == "true" and not is_loopback_url(values[url_key]):
            raise ValueError("Remote inference is blocked by local mode")
        if not values["ollama_model"].strip():
            raise ValueError("Choose or enter an Ollama model")
        if provider == "ollama_cloud" and values["local_only"] == "true":
            raise ValueError("Cloud inference requires local mode to be disabled")
    else:
        raise ValueError("Unknown assistant provider")
    if cancelled.is_set():
        raise SetupCancelled()
    speech_model = values.get("whisper_model", "")
    if speech_model:
        report("speech")
        from transcriber import model_path
        model_path(speech_model, download=True)
        if cancelled.is_set():
            raise SetupCancelled()
    if values.get("tts_mode") in ("tts", "both"):
        needed_lang = "fr" if values.get("language") == "fr" else "en"
        if not values.get("tts_voice_" + needed_lang):
            raise ValueError("Choose a voice for the selected language")
        if importlib.util.find_spec("piper") is None:
            raise RuntimeError("Piper is not installed")
        for lang in ("fr", "en"):
            voice = values.get("tts_voice_" + lang, "")
            if voice:
                report("voice " + lang)
                download_voice(voice, progress=(lambda done, total, stage="voice " + lang:
                                              progress(stage, done, total)) if progress else None)
        values["tts_engine"] = "piper"
    else:
        values["tts_engine"] = "off"
    if cancelled.is_set():
        raise SetupCancelled()
    values["setup_complete"] = "1"
    values.pop("llama_backend", None)
    values.pop("llama_catalog_model", None)
    values.pop("use_existing_binary", None)
    values.pop("use_existing_model", None)
    return values
