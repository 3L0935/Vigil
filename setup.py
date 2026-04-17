#!/usr/bin/env python3
"""WritHer Linux — first-run setup. Run with: uv run python setup.py"""

import os
import re
import sys
import subprocess
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
    {
        "name":    "Qwen2.5-1.5B Q4_K_M",
        "repo":    "bartowski/Qwen2.5-1.5B-Instruct-GGUF",
        "file":    "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf",
        "vram_mb": 1024,
    },
    {
        "name":    "Qwen2.5-3B Q4_K_M",
        "repo":    "bartowski/Qwen2.5-3B-Instruct-GGUF",
        "file":    "Qwen2.5-3B-Instruct-Q4_K_M.gguf",
        "vram_mb": 2200,
    },
    {
        "name":    "Qwen2.5-7B Q4_K_M",
        "repo":    "bartowski/Qwen2.5-7B-Instruct-GGUF",
        "file":    "Qwen2.5-7B-Instruct-Q4_K_M.gguf",
        "vram_mb": 4800,
    },
    {
        "name":    "Qwen2.5-14B Q4_K_M",
        "repo":    "bartowski/Qwen2.5-14B-Instruct-GGUF",
        "file":    "Qwen2.5-14B-Instruct-Q4_K_M.gguf",
        "vram_mb": 8800,
    },
    {
        "name":    "Qwen2.5-14B Q8_0",
        "repo":    "bartowski/Qwen2.5-14B-Instruct-GGUF",
        "file":    "Qwen2.5-14B-Instruct-Q8_0.gguf",
        "vram_mb": 15000,
    },
]

# Substrings that must ALL appear in the asset filename for each backend
LLAMA_ASSET_PATTERNS = {
    "cuda":   ["ubuntu", "cuda",   "x64"],
    "rocm":   ["ubuntu", "rocm",   "x64"],
    "vulkan": ["ubuntu", "vulkan", "x64"],
    "cpu":    ["ubuntu",           "x64"],
}
LLAMA_ASSET_EXCLUDES = {
    "cpu": ["cuda", "rocm", "vulkan"],
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
    patterns = LLAMA_ASSET_PATTERNS.get(backend, LLAMA_ASSET_PATTERNS["cpu"])
    excludes = LLAMA_ASSET_EXCLUDES.get(backend, [])
    for asset in data["assets"]:
        name = asset["name"].lower()
        if (all(p in name for p in patterns)
                and not any(e in name for e in excludes)
                and name.endswith(".zip")):
            return asset["browser_download_url"], asset["name"]
    raise RuntimeError(
        f"No llama.cpp asset found for '{backend}'. "
        "Use option [5] to point to an existing binary."
    )


def _download(url: str, dest: Path, label: str):
    def _progress(count, block, total):
        if total > 0:
            print(f"\r  {min(100, int(count * block * 100 / total))}%", end="", flush=True)
    urllib.request.urlretrieve(url, str(dest), _progress)
    print()


def _extract_llama_server(zip_path: Path, dest_dir: Path) -> Path:
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if "llama-server" in name and not name.endswith("/"):
                zf.extract(name, dest_dir)
                p = dest_dir / name
                p.chmod(0o755)
                return p
    raise RuntimeError("llama-server binary not found in archive")


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

    LLAMA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        url, filename = fetch_latest_llama_asset(chosen_backend)
    except RuntimeError as e:
        print(f"\nErreur : {e}")
        return Path(input("Chemin vers llama-server existant : ").strip()), False

    zip_dest = LLAMA_DIR / filename
    _download(url, zip_dest, filename)
    bin_path = _extract_llama_server(zip_dest, LLAMA_DIR)
    zip_dest.unlink()
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


def main():
    print("=== WritHer Linux — Setup ===\n")
    import database as db
    db.init()

    backend     = detect_gpu()
    total_vram  = get_total_vram_mb(backend)

    print(f"Backend GPU détecté : {backend.upper()}")
    if total_vram:
        print(f"VRAM totale : {total_vram} MB")
    else:
        print("Pas de GPU / mode CPU")

    bin_path, managed = setup_llama_binary()
    model_path        = setup_model(total_vram)

    db.save_setting("llama_server_bin",     str(bin_path))
    db.save_setting("llama_server_managed", "true" if managed else "false")
    db.save_setting("llama_model",          str(model_path))
    db.save_setting("llama_unload_timeout", "120")

    print("\n=== Configuration sauvegardée ===")
    print(f"  llama-server     : {bin_path}")
    print(f"  Modèle           : {model_path}")
    print(f"  Géré par WritHer : {'oui' if managed else 'non'}")
    print("\nLance l'app avec : uv run python main.py")


if __name__ == "__main__":
    if sys.stdin.isatty():
        main()
    else:
        # Invoked by setuptools as a build script — delegate to pyproject.toml config.
        from setuptools import setup
        setup()
