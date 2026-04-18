#!/usr/bin/env python3
"""WritHer Linux — first-run setup. Run with: uv run python setup.py"""

import fnmatch
import os
import re
import sys
import subprocess
import tarfile
import urllib.request
import json
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

WRITHER_DIR = Path.home() / ".local" / "share" / "writher"
LLAMA_DIR   = WRITHER_DIR / "llama"
MODELS_DIR  = WRITHER_DIR / "models"

LLAMA_RELEASES_API = "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"

MODEL_TIERS = [
    # CPU / ≤4 GB VRAM — Qwen3.5 0.8B, smallest with decent tool-calling
    {
        "name":    "Qwen3.5-0.8B Q4_K_M",
        "repo":    "bartowski/Qwen_Qwen3.5-0.8B-GGUF",
        "file":    "Qwen_Qwen3.5-0.8B-Q4_K_M.gguf",
        "vram_mb": 650,
    },
    # ≥5 GB VRAM — Qwen3.5 4B, good multilingual + tool-calling
    {
        "name":    "Qwen3.5-4B Q4_K_M",
        "repo":    "bartowski/Qwen_Qwen3.5-4B-GGUF",
        "file":    "Qwen_Qwen3.5-4B-Q4_K_M.gguf",
        "vram_mb": 2500,
    },
    # ≥10 GB VRAM — Qwen3.5 9B, sweet spot for assistant workloads
    # Note: Qwen3.5 may output <think> blocks; add /no_think to system prompt to disable
    {
        "name":    "Qwen3.5-9B Q4_K_M",
        "repo":    "bartowski/Qwen_Qwen3.5-9B-GGUF",
        "file":    "Qwen_Qwen3.5-9B-Q4_K_M.gguf",
        "vram_mb": 5500,
    },
    # ≥18 GB VRAM — same 9B at full 8-bit precision, noticeably better quality
    {
        "name":    "Qwen3.5-9B Q8_0",
        "repo":    "bartowski/Qwen_Qwen3.5-9B-GGUF",
        "file":    "Qwen_Qwen3.5-9B-Q8_0.gguf",
        "vram_mb": 10000,
    },
    # ≥24 GB VRAM — Mistral Small 3.2 24B, different model family, excellent tool-calling
    {
        "name":    "Mistral Small 3.2 24B Q4_K_M",
        "repo":    "bartowski/mistralai_Mistral-Small-3.2-24B-Instruct-2506-GGUF",
        "file":    "mistralai_Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf",
        "vram_mb": 13000,
    },
]

# Glob patterns for asset filenames (matched with fnmatch.fnmatch)
# cuda and cpu share the same base archive — CUDA support is embedded in it.
# Distinguish cpu from vulkan/rocm via exclude logic in fetch_latest_llama_asset.
BINARY_PATTERNS = {
    "cuda":   "llama-*-bin-ubuntu-x64.*",
    "rocm":   "llama-*-bin-ubuntu-rocm-*-x64.*",
    "vulkan": "llama-*-bin-ubuntu-vulkan-x64.*",
    "cpu":    "llama-*-bin-ubuntu-x64.*",
}


def detect_gpu() -> str:
    """Return 'cuda', 'rocm', 'vulkan', or 'cpu'."""
    for cmd, backend in [
        (["nvidia-smi"], "cuda"),
        (["rocm-smi"],   "rocm"),
        (["vulkaninfo"], "vulkan"),
    ]:
        try:
            r = subprocess.run(cmd, capture_output=True)
            if r.returncode == 0:
                return backend
        except FileNotFoundError:
            pass
    return "cpu"


def get_total_vram_mb(backend: str) -> int:
    """Return total GPU VRAM in MB, or 0 for CPU-only."""
    try:
        if backend == "cuda":
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, check=True,
            )
            return sum(int(x.strip()) for x in r.stdout.strip().splitlines() if x.strip())
        if backend in ("rocm", "vulkan"):  # AMD GPU, try sysfs first
            for vram_file in Path("/sys/class/drm").glob("*/device/mem_info_vram_total"):
                try:
                    vram_mb = int(vram_file.read_text().strip()) // (1024 * 1024)
                    if vram_mb > 0:
                        return vram_mb
                except (OSError, ValueError):
                    pass
            # Fallback: rocm-smi (rocm only)
            if backend == "rocm":
                r = subprocess.run(
                    ["rocm-smi", "--showmeminfo", "vram"],
                    capture_output=True, text=True,
                )
                total = 0
                for m in re.findall(r"VRAM Total Memory \(B\):\s*(\d+)", r.stdout):
                    total += int(m) // (1024 * 1024)
                return total
    except Exception:
        pass
    return 0


def select_model_tier(total_vram_mb: int) -> dict:
    """Return largest model tier fitting within 55% of total_vram_mb."""
    budget = int(total_vram_mb * 0.55)
    eligible = [t for t in MODEL_TIERS if t["vram_mb"] <= budget]
    return eligible[-1] if eligible else MODEL_TIERS[0]


def fetch_latest_llama_asset(backend: str) -> tuple[str, str]:
    """Return (download_url, filename) for the latest llama.cpp release."""
    with urllib.request.urlopen(LLAMA_RELEASES_API) as resp:
        data = json.load(resp)
    pattern = BINARY_PATTERNS.get(backend, BINARY_PATTERNS["cpu"])
    for asset in data["assets"]:
        name = asset["name"]
        if not fnmatch.fnmatch(name, pattern):
            continue
        # For cpu: exclude vulkan/rocm builds that also match the base pattern
        if backend == "cpu" and any(x in name.lower() for x in ("vulkan", "rocm")):
            continue
        return asset["browser_download_url"], asset["name"]
    available = [a["name"] for a in data["assets"]]
    raise RuntimeError(
        f"No llama.cpp asset found for '{backend}' (pattern: {pattern!r}). "
        f"Available: {available}. "
        "Use option [5] to point to an existing binary."
    )


def _download(url: str, dest: Path):
    def _progress(count, block, total):
        if total > 0:
            print(f"\r  {min(100, int(count * block * 100 / total))}%", end="", flush=True)
    urllib.request.urlretrieve(url, str(dest), _progress)
    print()


def _extract_llama_server(archive_path: Path, dest_dir: Path) -> Path:
    _BIN_TARGETS = {"llama-server", "llama-server.exe"}

    def _should_extract(filename: str) -> bool:
        if filename in _BIN_TARGETS:
            return True
        return filename.endswith(".dylib") or ".so" in filename

    if archive_path.suffix == ".zip":
        with zipfile.ZipFile(archive_path) as zf:
            for member in zf.namelist():
                filename = Path(member).name
                if _should_extract(filename):
                    dest = dest_dir / filename
                    dest.write_bytes(zf.read(member))
                    dest.chmod(0o755)
    elif archive_path.suffixes[-2:] == [".tar", ".gz"]:
        with tarfile.open(archive_path) as tf:
            for member in tf.getmembers():
                filename = Path(member.name).name
                if _should_extract(filename):
                    fobj = tf.extractfile(member)
                    if fobj is not None:
                        dest = dest_dir / filename
                        dest.write_bytes(fobj.read())
                        dest.chmod(0o755)

    for candidate in ("llama-server", "llama-server.exe"):
        p = dest_dir / candidate
        if p.exists():
            return p
    raise RuntimeError(
        f"llama-server binary not found after extraction. "
        f"Files present: {[f.name for f in dest_dir.iterdir()]}"
    )


def setup_llama_binary() -> tuple[Path, bool]:
    """Ask user to download or point to llama-server. Returns (path, managed)."""
    detected = detect_gpu()
    BUILD_ORDER  = ["cpu", "vulkan", "rocm", "cuda"]
    BUILD_LABELS = {
        "cpu":    "CPU         (universel, lent)",
        "vulkan": "Vulkan      (GPU générique)",
        "rocm":   "ROCm        (AMD)",
        "cuda":   "CUDA        (NVIDIA)",
    }
    print("\n=== llama-server ===")
    print("Builds disponibles :")
    for i, key in enumerate(BUILD_ORDER, 1):
        marker = " <- recommandé" if key == detected else ""
        print(f"  [{i}] {BUILD_LABELS[key]}{marker}")
    print(f"  [5] Pointer vers un llama-server existant")

    rec_idx = str(BUILD_ORDER.index(detected) + 1)
    choice  = input(f"\nChoix [Entrée = {rec_idx}] : ").strip() or rec_idx

    if choice == "5":
        return Path(input("Chemin vers llama-server : ").strip()), False
    if choice in ("1", "2", "3", "4"):
        chosen_backend = BUILD_ORDER[int(choice) - 1]
    else:
        chosen_backend = detected

    # Return existing binary if already installed
    existing = LLAMA_DIR / "llama-server"
    if existing.exists():
        print(f"  llama-server already installed: {existing}")
        return existing, True

    LLAMA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        url, filename = fetch_latest_llama_asset(chosen_backend)
    except RuntimeError as e:
        print(f"\nErreur : {e}")
        return Path(input("Chemin vers llama-server existant : ").strip()), False

    archive_dest = LLAMA_DIR / filename
    _download(url, archive_dest)
    bin_path = _extract_llama_server(archive_dest, LLAMA_DIR)
    archive_dest.unlink()
    print(f"  llama-server installé : {bin_path}")
    return bin_path, True


def setup_model(total_vram_mb: int) -> Path:
    """Ask user to pick/download a model. Returns path to .gguf."""
    recommended = select_model_tier(total_vram_mb)
    budget = int(total_vram_mb * 0.55)

    print("\n=== Modèle LLM ===")
    if total_vram_mb:
        print(f"VRAM totale : {total_vram_mb} MB  |  budget (55%) : {budget} MB\n")
    else:
        print("Mode CPU — pas de GPU détecté\n")

    print("Modèles disponibles :")
    for i, tier in enumerate(MODEL_TIERS, 1):
        fits   = "OK" if tier["vram_mb"] <= budget else "X"
        marker = " <- recommandé" if tier["name"] == recommended["name"] else ""
        print(f"  [{i}] {fits} {tier['name']:35s} (~{tier['vram_mb']} MB){marker}")
    print(f"  [{len(MODEL_TIERS)+1}] Pointer vers un fichier .gguf existant")

    rec_idx = str(MODEL_TIERS.index(recommended) + 1)
    choice  = input(f"\nChoix [Entrée = {rec_idx}] : ").strip() or rec_idx

    if choice == str(len(MODEL_TIERS) + 1):
        return Path(input("Chemin vers le fichier .gguf : ").strip())
    if choice.isdigit() and 1 <= int(choice) <= len(MODEL_TIERS):
        chosen = MODEL_TIERS[int(choice) - 1]
    else:
        chosen = recommended

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    dest = MODELS_DIR / chosen["file"]
    if dest.exists():
        print(f"  Modèle déjà présent : {dest}")
        return dest

    from huggingface_hub import hf_hub_download
    print(f"  Téléchargement {chosen['name']} depuis HuggingFace...")
    downloaded = hf_hub_download(
        repo_id=chosen["repo"],
        filename=chosen["file"],
        local_dir=str(MODELS_DIR),
    )
    print(f"  Modèle installé : {downloaded}")
    return Path(downloaded)


_WHISPER_MODELS = [
    ("tiny",     "~75 MB,  fastest, lower accuracy"),
    ("base",     "~145 MB, fast, decent accuracy       <- recommended"),
    ("small",    "~466 MB, good balance"),
    ("medium",   "~1.5 GB, high accuracy"),
    ("large-v3", "~3 GB,   best accuracy, slow on CPU"),
]


def setup_language() -> str:
    """Phase 0 — Choose UI language. Saved to DB."""
    import database as db
    import config
    print("=== Language / Langue ===\n")
    print("  [1] English")
    print("  [2] Français")
    print("  [3] Italiano")
    choice = input("\nChoice / Choix [1]: ").strip() or "1"
    lang = {"1": "en", "2": "fr", "3": "it"}.get(choice, "en")
    db.save_setting("language", lang)
    config.LANGUAGE = lang
    return lang


def setup_whisper() -> str:
    """Phase 2.5 — Choose Whisper model size."""
    import database as db
    import config
    print("\n=== Whisper (speech recognition) ===\n")
    print("Choose a model size (downloaded automatically on first use):\n")
    for i, (name, desc) in enumerate(_WHISPER_MODELS, 1):
        print(f"  [{i}] {name:<10} — {desc}")
    choice = input("\nChoice [2]: ").strip() or "2"
    idx = int(choice) - 1 if choice.isdigit() and 1 <= int(choice) <= 5 else 1
    model = _WHISPER_MODELS[idx][0]
    db.save_setting("whisper_model", model)
    config.MODEL_SIZE = model
    print(f"  Whisper model: {model}")
    return model


def _piper_voice_url(voice: str) -> str:
    lang_full, rest = voice.split("-", 1)
    lang_short = lang_full.split("_")[0].lower()
    speaker, quality = rest.rsplit("-", 1)
    return (
        "https://huggingface.co/rhasspy/piper-voices"
        f"/resolve/main/{lang_short}/{lang_full}/{speaker}/{quality}/{voice}"
    )


def _download_piper_voice(voice: str) -> None:
    dest_dir = WRITHER_DIR / "tts" / "piper"
    dest_dir.mkdir(parents=True, exist_ok=True)
    base = _piper_voice_url(voice)
    for ext in (".onnx", ".onnx.json"):
        dest = dest_dir / f"{voice}{ext}"
        if not dest.exists():
            print(f"  Downloading {voice}{ext}...")
            _download(base + ext, dest)
    print(f"  {voice} installed.")


def setup_tts() -> None:
    """Phase 3 — Choose TTS engine, voices, and display mode."""
    import database as db
    from tts import _BUILTIN_VOICES
    print("\n=== TTS (Text-to-Speech) ===\n")
    print("Choose a TTS engine, or skip:\n")
    print("  Piper TTS")
    print("    + Best French voice quality, ~50 ms latency")
    print("    + Modular: download only the voices you need (~80 MB/voice)")
    print("    - Requires downloading voice files separately\n")
    print("  Kokoro")
    print("    + Best English voice quality, all voices bundled")
    print("    + Single install (~300 MB total, no per-voice downloads)")
    print("    - French quality decent but not best-in-class\n")
    print("  [1] Piper TTS")
    print("  [2] Kokoro")
    print("  [3] No TTS (overlay only — skip)")

    choice = input("\nChoice [3]: ").strip() or "3"

    if choice == "3":
        db.save_setting("tts_engine", "off")
        db.save_setting("tts_mode",   "overlay")
        print("  TTS skipped — overlay mode active.")
        return

    engine = "piper" if choice == "1" else "kokoro"

    for lang in ("fr", "en"):
        voices = _BUILTIN_VOICES[engine][lang]
        print(f"\n  {lang.upper()} voices:")
        for i, v in enumerate(voices, 1):
            print(f"    [{i}] {v}")
        vchoice = input(f"  Choice [1]: ").strip() or "1"
        idx = int(vchoice) - 1 if vchoice.isdigit() and 1 <= int(vchoice) <= len(voices) else 0
        voice = voices[idx]
        db.save_setting(f"tts_voice_{lang}", voice)
        print(f"  {lang.upper()} voice: {voice}")

    print("\n  Display mode:")
    print("  [1] TTS only     (no overlay)")
    print("  [2] Overlay only (TTS audio muted)")
    print("  [3] Both         (TTS + overlay text)")
    mchoice = input("  Choice [3]: ").strip() or "3"
    mode = {"1": "tts", "2": "overlay", "3": "both"}.get(mchoice, "both")

    db.save_setting("tts_engine", engine)
    db.save_setting("tts_mode",   mode)
    print(f"  Engine: {engine}  Mode: {mode}")

    if engine == "piper":
        print("\n  Installing piper-tts...")
        subprocess.run(["uv", "sync", "--extra", "tts-piper"], check=True)
        for lang in ("fr", "en"):
            import database as _db
            voice = _db.get_setting(f"tts_voice_{lang}", "")
            if voice:
                _download_piper_voice(voice)
    else:
        print("\n  Installing kokoro (~300 MB)...")
        subprocess.run(["uv", "sync", "--extra", "tts-kokoro"], check=True)
        print("  Kokoro installed.")


def main():
    print("=== WritHer Linux — Setup ===\n")
    import database as db
    db.init()

    # Phase 0 — Language
    setup_language()

    # Phase 1 — llama-server binary
    backend    = detect_gpu()
    total_vram = get_total_vram_mb(backend)
    print(f"\nGPU backend detected: {backend.upper()}")
    if total_vram:
        print(f"Total VRAM: {total_vram} MB")
    else:
        print("No GPU / CPU mode")

    bin_path, managed = setup_llama_binary()

    # Phase 2 — LLM model
    model_path = setup_model(total_vram)

    # Phase 2.5 — Whisper model
    setup_whisper()

    # Phase 3 — TTS
    setup_tts()

    db.save_setting("llama_server_bin",     str(bin_path))
    db.save_setting("llama_server_managed", "true" if managed else "false")
    db.save_setting("llama_model",          str(model_path))
    db.save_setting("llama_unload_timeout", "120")

    print("\n=== Configuration saved ===")
    print(f"  llama-server : {bin_path}")
    print(f"  Model        : {model_path}")
    print(f"  Managed      : {'yes' if managed else 'no'}")
    print("\nRun the app with: uv run python main.py")


if __name__ == "__main__":
    if sys.stdin.isatty():
        main()
    else:
        # Invoked by setuptools as a build script — delegate to pyproject.toml config.
        from setuptools import setup
        setup()
