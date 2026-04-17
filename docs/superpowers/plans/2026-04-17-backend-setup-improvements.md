# WritHer Backend & Setup Improvements — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add llama.cpp lifecycle management, a first-run setup script, toggle-only recording, and model selection in settings.

**Architecture:** New `llm_manager.py` owns llama-server spawn/kill via inactivity timer; `setup.py` detects hardware and downloads the right llama.cpp binary + model; `settings_window.py` gains Whisper and LLM model controls; hold mode is removed entirely from hotkey and main.

**Tech Stack:** Python 3.8+, faster-whisper, requests, huggingface-hub, subprocess, CustomTkinter, SQLite (settings KV)

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `llm_manager.py` | Create | LlamaServerManager: spawn, health check, inactivity timer, shutdown |
| `setup.py` | Create | CLI first-run: GPU detect, llama.cpp binary download, model download |
| `hotkey.py` | Modify | Remove hold mode branches, simplify to toggle-only |
| `main.py` | Modify | Remove timeout system, integrate LlamaServerManager, hot-swap Transcriber |
| `config.py` | Modify | Remove HOLD_TO_RECORD, MAX_RECORD_SECONDS |
| `assistant.py` | Modify | Call manager.ensure_running() before LLM calls |
| `settings_window.py` | Modify | Remove hold/toggle UI, add Whisper dropdown + LLM model + timeout |
| `tests/test_llm_manager.py` | Create | Unit tests for LlamaServerManager |
| `tests/test_setup_detect.py` | Create | Unit tests for GPU detection + model tier selection |

---

### Task 1: Toggle-only — hotkey.py + main.py + config.py

**Files:**
- Modify: `hotkey.py`
- Modify: `main.py`
- Modify: `config.py`

- [ ] **Step 1: Simplify hotkey.py — remove hold mode**

Replace `_handle_press`, `_handle_release`, remove `_is_hold_mode`, `force_stop_dictation`, `force_stop_assistant`. Update the module docstring.

```python
# hotkey.py — replace _handle_press (was lines 37-69)
def _handle_press(self, key):
    if key == config.HOTKEY:
        if self._dict_pressed:
            return  # ignore key-repeat
        self._dict_pressed = True
        if not self._dict_recording:
            self._dict_recording = True
            self._safe_call(self._on_press, "Dictation toggle-start")
        else:
            self._dict_recording = False
            self._safe_call(self._on_release, "Dictation toggle-stop")

    elif key == config.ASSISTANT_HOTKEY and self._on_assist_press:
        if self._assist_pressed:
            return
        self._assist_pressed = True
        if not self._assist_recording:
            self._assist_recording = True
            self._safe_call(self._on_assist_press, "Assistant toggle-start")
        else:
            self._assist_recording = False
            self._safe_call(self._on_assist_release, "Assistant toggle-stop")

# replace _handle_release (was lines 73-89)
def _handle_release(self, key):
    if key == config.HOTKEY:
        self._dict_pressed = False
    elif key == config.ASSISTANT_HOTKEY:
        self._assist_pressed = False
```

Also update the docstring at line 1 — remove all mention of hold mode and `HOLD_TO_RECORD`.

- [ ] **Step 2: Remove timeout system from main.py**

Remove global declarations (lines 54-55):
```python
# DELETE these two lines:
_dict_timeout_timer  = None
_assist_timeout_timer = None
```

Remove functions `_start_timeout` (lines 88-103), `_cancel_timeout` (lines 106-113), `_timeout_dictation` (lines 116-119), `_timeout_assistant` (lines 122-125).

Remove `_MIN_DURATION = 0.5` (line 52) and `_rec_start = 0.0` (line 51).

In `_on_hotkey_press`: remove `_rec_start = time.monotonic()` and `_start_timeout("dictation")`.

In `_on_hotkey_release`: remove `_cancel_timeout("dictation")`, remove `duration = time.monotonic() - _rec_start`, remove the `duration >= _MIN_DURATION` check — put audio on queue if non-empty only:
```python
def _on_hotkey_release():
    audio = recorder.stop()
    if tray:
        tray.set_recording(False)
    if audio is not None and len(audio) > 0:
        if widget:
            widget.show_processing()
        _pipeline_queue.put(audio)
    else:
        if widget:
            widget.hide()
```

Apply same pattern to `_on_assist_press` / `_on_assist_release`.

In `_quit()`, remove `_cancel_timeout("dictation")` and `_cancel_timeout("assistant")` (lines 314-315).

In `_load_settings()`, remove the `hold` block (lines 63-65) and `max_sec` block (lines 66-71).

- [ ] **Step 3: Remove HOLD_TO_RECORD and MAX_RECORD_SECONDS from config.py**

Delete lines 41-45:
```python
# DELETE:
# ── Recording mode ────────────────────────────────────────────────────────
HOLD_TO_RECORD = True
MAX_RECORD_SECONDS = 120
```

- [ ] **Step 4: Run the app and verify toggle works**

```bash
uv run python main.py
```

Press dictation hotkey once → recording starts (widget visible). Press again → stops and transcribes. No errors in log. No hold mode.

- [ ] **Step 5: Commit**

```bash
git add hotkey.py main.py config.py
git commit -m "feat: toggle-only recording, remove hold mode and timeout system"
```

---

### Task 2: LlamaServerManager

**Files:**
- Create: `llm_manager.py`
- Create: `tests/test_llm_manager.py`
- Modify: `assistant.py` (add ensure_running call)
- Modify: `main.py` (import + shutdown on quit)

- [ ] **Step 1: Write failing tests**

Create `tests/` directory if absent, then create `tests/test_llm_manager.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_ensure_running_managed_spawns_process():
    """ensure_running() spawns subprocess when managed=true and no process running."""
    from llm_manager import LlamaServerManager
    mgr = LlamaServerManager()

    with patch("llm_manager.db") as mock_db, \
         patch("llm_manager.subprocess.Popen") as mock_popen, \
         patch.object(mgr, "_wait_health"), \
         patch.object(mgr, "_reset_timer"):
        mock_db.get_setting.side_effect = lambda key, default="": {
            "llama_server_managed": "true",
            "llama_server_bin":     "/usr/bin/llama-server",
            "llama_model":          "/models/qwen.gguf",
            "llama_unload_timeout": "120",
        }.get(key, default)
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc

        mgr.ensure_running()

        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert "/usr/bin/llama-server" in args
        assert "/models/qwen.gguf" in args


def test_ensure_running_unmanaged_does_not_spawn():
    """ensure_running() does NOT spawn when managed=false."""
    from llm_manager import LlamaServerManager
    mgr = LlamaServerManager()

    with patch("llm_manager.db") as mock_db, \
         patch("llm_manager.subprocess.Popen") as mock_popen, \
         patch.object(mgr, "_wait_health"), \
         patch.object(mgr, "_reset_timer"):
        mock_db.get_setting.side_effect = lambda key, default="": {
            "llama_server_managed": "false",
        }.get(key, default)

        mgr.ensure_running()
        mock_popen.assert_not_called()


def test_auto_shutdown_kills_process():
    """_auto_shutdown() terminates the managed process."""
    from llm_manager import LlamaServerManager
    mgr = LlamaServerManager()
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mgr._process = mock_proc

    mgr._auto_shutdown()

    mock_proc.terminate.assert_called_once()


def test_timeout_zero_never_schedules_timer():
    """timeout=0 means never unload — no Timer is created."""
    from llm_manager import LlamaServerManager
    mgr = LlamaServerManager()

    with patch("llm_manager.db") as mock_db, \
         patch("llm_manager.threading.Timer") as mock_timer:
        mock_db.get_setting.return_value = "0"
        mgr._reset_timer()
        mock_timer.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/elo/github/WritHer-Linux && uv run pytest tests/test_llm_manager.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'llm_manager'`

- [ ] **Step 3: Create llm_manager.py**

```python
import subprocess
import threading
import time
import urllib.parse

import requests

import database as db
from logger import log


class LlamaServerManager:
    def __init__(self):
        self._process: subprocess.Popen | None = None
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    # ── DB-backed properties (read at call time) ──────────────────────────

    def _is_managed(self) -> bool:
        return db.get_setting("llama_server_managed", "true") == "true"

    def _bin_path(self) -> str:
        return db.get_setting("llama_server_bin", "")

    def _model_path(self) -> str:
        return db.get_setting("llama_model", "")

    def _timeout_sec(self) -> int:
        try:
            return int(db.get_setting("llama_unload_timeout", "120"))
        except ValueError:
            return 120

    def _server_url(self) -> str:
        import config
        return getattr(config, "LLAMA_SERVER_URL", "http://localhost:8080")

    # ── Public API ────────────────────────────────────────────────────────

    def ensure_running(self):
        """Start server if needed, then reset inactivity timer."""
        with self._lock:
            if self._is_managed():
                if self._process is None or self._process.poll() is not None:
                    self._spawn()
            else:
                self._wait_health(timeout=5)
        self._reset_timer()

    def shutdown(self):
        """Immediately stop the managed server process."""
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
            log.info("llama-server stopped.")

    # ── Internal ──────────────────────────────────────────────────────────

    def _spawn(self):
        bin_path  = self._bin_path()
        model_path = self._model_path()
        if not bin_path or not model_path:
            raise RuntimeError(
                "llama_server_bin or llama_model not configured — run setup.py first."
            )
        port = urllib.parse.urlparse(self._server_url()).port or 8080
        cmd = [bin_path, "--model", model_path,
               "--port", str(port), "--host", "127.0.0.1"]
        log.info("Spawning llama-server: %s", " ".join(cmd))
        self._process = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        self._wait_health(timeout=30)
        log.info("llama-server ready.")

    def _wait_health(self, timeout: int):
        health_url = self._server_url().rstrip("/") + "/health"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                r = requests.get(health_url, timeout=2)
                if r.status_code == 200:
                    return
            except Exception:
                pass
            time.sleep(0.5)
        raise RuntimeError(f"llama-server not ready after {timeout}s")

    def _reset_timer(self):
        if self._timer is not None:
            self._timer.cancel()
        timeout = self._timeout_sec()
        if timeout <= 0:
            return
        self._timer = threading.Timer(timeout, self._auto_shutdown)
        self._timer.daemon = True
        self._timer.start()

    def _auto_shutdown(self):
        with self._lock:
            self.shutdown()
        log.info("llama-server auto-unloaded after inactivity.")


# Module-level singleton
manager = LlamaServerManager()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_llm_manager.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Integrate into assistant.py**

Add import after existing imports (after `from llm_backend import LlamaServerBackend`):
```python
from llm_manager import manager as _llm_manager
```

Add `_llm_manager.ensure_running()` as first line of `process()` (line 300):
```python
def process(text: str) -> str:
    _llm_manager.ensure_running()
    log.info("Assistant input: %r", text)
    # ... rest unchanged
```

- [ ] **Step 6: Add manager.shutdown() to main.py _quit()**

Add import at top of `main.py` (after `import assistant`):
```python
from llm_manager import manager as _llm_manager
```

In `_quit()`, add before `_pipeline_queue.put(_STOP)`:
```python
    _llm_manager.shutdown()
```

- [ ] **Step 7: Commit**

```bash
git add llm_manager.py tests/test_llm_manager.py assistant.py main.py
git commit -m "feat: LlamaServerManager — auto-load/unload llama-server with inactivity timer"
```

---

### Task 3: Setup CLI (setup.py)

**Files:**
- Create: `setup.py`
- Create: `tests/test_setup_detect.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_setup_detect.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_detect_gpu_cuda():
    """Returns 'cuda' when nvidia-smi exits 0."""
    import setup
    with patch("setup.subprocess.run", return_value=MagicMock(returncode=0)):
        assert setup.detect_gpu() == "cuda"


def test_detect_gpu_rocm():
    """Returns 'rocm' when nvidia-smi fails but rocm-smi exits 0."""
    import setup
    def side_effect(cmd, **kwargs):
        r = MagicMock()
        r.returncode = 0 if cmd[0] == "rocm-smi" else 1
        return r
    with patch("setup.subprocess.run", side_effect=side_effect):
        assert setup.detect_gpu() == "rocm"


def test_detect_gpu_cpu_fallback():
    """Returns 'cpu' when all GPU tools return non-zero."""
    import setup
    with patch("setup.subprocess.run", return_value=MagicMock(returncode=1)):
        assert setup.detect_gpu() == "cpu"


def test_select_model_tier_8gb():
    """8 GB VRAM → budget 4505 MB → Qwen2.5-3B fits, Qwen2.5-7B does not."""
    import setup
    result = setup.select_model_tier(total_vram_mb=8192)
    assert result["name"] == "Qwen2.5-3B Q4_K_M"


def test_select_model_tier_20gb():
    """20 GB VRAM → budget 11264 MB → Qwen2.5-14B Q4_K_M fits."""
    import setup
    result = setup.select_model_tier(total_vram_mb=20480)
    assert result["name"] == "Qwen2.5-14B Q4_K_M"


def test_select_model_tier_cpu_only():
    """0 MB VRAM → returns smallest model."""
    import setup
    result = setup.select_model_tier(total_vram_mb=0)
    assert result["name"] == "Qwen2.5-1.5B Q4_K_M"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_setup_detect.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'setup'`

- [ ] **Step 3: Create setup.py**

```python
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
        marker = " ← recommandé" if key == detected else ""
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
        fits   = "✓" if tier["vram_mb"] <= budget else "✗"
        marker = " ← recommandé" if tier["name"] == recommended["name"] else ""
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
    main()
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_setup_detect.py -v
```

Expected: 6 PASSED

- [ ] **Step 5: Smoke test detection (no download)**

```bash
uv run python -c "
import setup
gpu = setup.detect_gpu()
vram = setup.get_total_vram_mb(gpu)
model = setup.select_model_tier(vram)
print(f'GPU: {gpu}, VRAM: {vram} MB, Recommended: {model[\"name\"]}')
"
```

Expected: prints detected GPU and a model name, no errors.

- [ ] **Step 6: Commit**

```bash
git add setup.py tests/test_setup_detect.py
git commit -m "feat: setup.py — hardware detection, llama.cpp binary download, model tier selection"
```

---

### Task 4: Settings UI — Whisper + LLM

**Files:**
- Modify: `settings_window.py`
- Modify: `main.py`

- [ ] **Step 1: Add whisper_model to _load_settings() and hot-swap callback in main.py**

In `_load_settings()`, add after the `lang` block:
```python
    whisper = db.get_setting("whisper_model", "")
    if whisper:
        config.MODEL_SIZE = whisper
```

Add new function in `main.py` (after `_load_settings`):
```python
def _on_whisper_model_change(model_name: str):
    global transcriber
    config.MODEL_SIZE = model_name
    db.save_setting("whisper_model", model_name)
    log.info("Whisper model changed to %s, reloading...", model_name)
    transcriber = Transcriber()
    log.info("Whisper model reloaded.")
```

Update `SettingsWindow` instantiation in `main()`:
```python
settings_win = SettingsWindow(root, on_whisper_change=_on_whisper_model_change)
```

- [ ] **Step 2: Update SettingsWindow constructor and add new attributes**

Change the class definition in `settings_window.py`:

```python
# Change _WIN_H:
_WIN_W, _WIN_H = 480, 640

class SettingsWindow:
    def __init__(self, root: tk.Tk, on_whisper_change=None):
        self._root = root
        self._win = None
        self._drag_x = 0
        self._drag_y = 0
        self._title_eye_tk = None
        self._on_whisper_change_cb = on_whisper_change
        self._llm_url_var = None
        self._vault_path_var = None
        self._lang_var = None
        self._overlay_pos_var = None
        self._whisper_var = None
        self._llm_model_var = None
        self._llm_timeout_var = None
```

- [ ] **Step 3: Replace _build() content — remove hold/toggle, add Whisper + LLM sections**

In `_build()`, remove entirely:
- The "Recording mode" label block (lines 122-147)
- The first separator (lines 149-151)
- The `_slider_section` block (lines 153-177)
- The second separator (lines 179-181)

Keep: LLM Server URL section, Obsidian Vault section, Language section, Overlay Position section, Save button.

Add after the LLM Server URL section and before Obsidian Vault, insert these two new sections:

```python
# ── Whisper Model ──────────────────────────────────────────────────
ctk.CTkFrame(pad, fg_color=T.BORDER, height=1, corner_radius=0).pack(
    fill="x", pady=(0, T.PAD_M))
ctk.CTkLabel(pad, text="Whisper model",
             font=T.FONT_TITLE, text_color=T.FG,
             anchor="w").pack(fill="x", pady=(0, T.PAD_M))
self._whisper_var = tk.StringVar(value=getattr(config, "MODEL_SIZE", "base"))
ctk.CTkOptionMenu(
    pad,
    values=["tiny", "base", "small", "medium", "large-v3"],
    variable=self._whisper_var,
    fg_color=T.BG_CARD, button_color=T.BG_HOVER,
    button_hover_color=T.BG_HOVER, text_color=T.FG,
    dropdown_fg_color=T.BG_CARD, dropdown_text_color=T.FG,
    dropdown_hover_color=T.BG_HOVER,
    font=T.FONT_SMALL, corner_radius=6,
    command=self._on_whisper_change,
).pack(fill="x", pady=(0, T.PAD_L))

# ── LLM Model ──────────────────────────────────────────────────────
ctk.CTkFrame(pad, fg_color=T.BORDER, height=1, corner_radius=0).pack(
    fill="x", pady=(0, T.PAD_M))
ctk.CTkLabel(pad, text="Modèle LLM (.gguf)",
             font=T.FONT_TITLE, text_color=T.FG,
             anchor="w").pack(fill="x", pady=(0, T.PAD_M))
llm_row = ctk.CTkFrame(pad, fg_color="transparent")
llm_row.pack(fill="x", pady=(0, T.PAD_L))
self._llm_model_var = tk.StringVar(value=db.get_setting("llama_model", ""))
ctk.CTkEntry(llm_row, textvariable=self._llm_model_var,
             fg_color=T.BG_INPUT, border_color=T.BORDER,
             text_color=T.FG, font=T.FONT_SMALL,
             height=32, corner_radius=6).pack(
    side="left", fill="x", expand=True, padx=(0, T.PAD_M))
ctk.CTkButton(llm_row, text="Browse", width=80, height=32,
              fg_color=T.BG_CARD, hover_color=T.BG_HOVER,
              border_color=T.BORDER, border_width=1,
              text_color=T.FG, font=T.FONT_SMALL, corner_radius=6,
              command=self._browse_model).pack(side="right")

# ── LLM Unload Timeout ────────────────────────────────────────────
ctk.CTkFrame(pad, fg_color=T.BORDER, height=1, corner_radius=0).pack(
    fill="x", pady=(0, T.PAD_M))
ctk.CTkLabel(pad, text="Déchargement LLM (inactivité)",
             font=T.FONT_TITLE, text_color=T.FG,
             anchor="w").pack(fill="x", pady=(0, T.PAD_M))
self._llm_timeout_var = tk.StringVar(
    value=db.get_setting("llama_unload_timeout", "120"))
ctk.CTkOptionMenu(
    pad,
    values=["60", "120", "300", "0"],
    variable=self._llm_timeout_var,
    fg_color=T.BG_CARD, button_color=T.BG_HOVER,
    button_hover_color=T.BG_HOVER, text_color=T.FG,
    dropdown_fg_color=T.BG_CARD, dropdown_text_color=T.FG,
    dropdown_hover_color=T.BG_HOVER,
    font=T.FONT_SMALL, corner_radius=6,
    command=self._on_llm_timeout_change,
).pack(fill="x", pady=(0, T.PAD_L))
```

- [ ] **Step 4: Replace _sync_ui, remove dead methods, add new callbacks**

Replace `_sync_ui`:
```python
def _sync_ui(self):
    if self._whisper_var:
        self._whisper_var.set(
            db.get_setting("whisper_model", getattr(config, "MODEL_SIZE", "base")))
    if self._llm_model_var:
        self._llm_model_var.set(db.get_setting("llama_model", ""))
    if self._llm_timeout_var:
        self._llm_timeout_var.set(db.get_setting("llama_unload_timeout", "120"))
```

Remove methods: `_set_mode`, `_on_slider_change`, `_update_mode_buttons`, `_update_slider_visibility`.

Add new callbacks:
```python
def _on_whisper_change(self, value: str):
    if self._on_whisper_change_cb:
        self._on_whisper_change_cb(value)

def _browse_model(self):
    path = fd.askopenfilename(
        title="Select GGUF model",
        filetypes=[("GGUF files", "*.gguf"), ("All files", "*")],
    )
    if path and self._llm_model_var:
        self._llm_model_var.set(path)

def _on_llm_timeout_change(self, value: str):
    db.save_setting("llama_unload_timeout", value)
    log.info("LLM unload timeout set to %ss", value)
```

Update `_save_linux_settings` — add LLM model save + restart manager if changed, remove hold_to_record / max_record_seconds:
```python
def _save_linux_settings(self):
    if self._llm_url_var:
        url = self._llm_url_var.get().strip()
        if url:
            config.LLAMA_SERVER_URL = url
            db.save_setting("llama_server_url", url)
    if self._llm_model_var:
        model = self._llm_model_var.get().strip()
        if model:
            old = db.get_setting("llama_model", "")
            db.save_setting("llama_model", model)
            if model != old:
                from llm_manager import manager as _mgr
                _mgr.shutdown()
    if self._vault_path_var:
        path = self._vault_path_var.get().strip()
        config.OBSIDIAN_VAULT_PATH = path
        db.save_setting("obsidian_vault_path", path)
    if self._lang_var:
        lang = self._lang_var.get()
        config.LANGUAGE = lang
        db.save_setting("language", lang)
    if self._overlay_pos_var:
        pos = self._overlay_pos_var.get()
        config.OVERLAY_POSITION = pos
        db.save_setting("overlay_position", pos)
    log.info("Settings saved.")
```

- [ ] **Step 5: Launch and verify settings UI**

```bash
uv run python main.py
```

Open settings via tray icon. Verify:
- No hold/toggle buttons visible
- Whisper model dropdown shows tiny/base/small/medium/large-v3, current value = config.MODEL_SIZE
- LLM model field shows value from DB (or empty if setup.py not run yet)
- Browse button opens file picker for .gguf files
- LLM timeout dropdown shows 60/120/300/0
- Changing Whisper model → log shows "Whisper model reloaded"
- Save button persists all values

- [ ] **Step 6: Commit**

```bash
git add settings_window.py main.py
git commit -m "feat: settings — Whisper model selection, LLM model path, unload timeout; remove hold mode UI"
```

---

## Spec Coverage Check

| Spec requirement | Task |
|-----------------|------|
| Toggle-only recording | Task 1 |
| Remove hold mode completely | Task 1 |
| Setup CLI — detect GPU backend | Task 3 |
| Setup CLI — all builds shown, suggestion marked | Task 3 |
| Setup CLI — point to existing binary | Task 3 |
| Setup CLI — download llama.cpp from GitHub releases | Task 3 |
| Setup CLI — model tier selection (total_vram × 0.55) | Task 3 |
| Setup CLI — download model via huggingface-hub | Task 3 |
| LlamaServerManager — spawn on first call | Task 2 |
| LlamaServerManager — inactivity timer auto-shutdown | Task 2 |
| LlamaServerManager — managed=false health-check only | Task 2 |
| LlamaServerManager — timeout=0 never unloads | Task 2 |
| Settings — Whisper model dropdown with hot-swap | Task 4 |
| Settings — LLM model path + browse | Task 4 |
| Settings — LLM unload timeout | Task 4 |
