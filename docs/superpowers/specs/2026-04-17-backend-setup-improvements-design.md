# WritHer — Backend & Setup Improvements

**Date:** 2026-04-17
**Status:** Approved

---

## Scope

Five focused changes to improve reliability, hardware setup, and UX:

1. Toggle-only recording (remove hold mode)
2. Setup CLI (`setup.py`) — llama.cpp binary + model download/detection
3. `LlamaServerManager` — auto-load/unload llama-server with inactivity timeout
4. Whisper model selection in settings
5. LLM model + timeout selection in settings

---

## 1. Toggle-only Recording

**Problem:** Hold mode is broken and toggle is the only useful mode in practice.

**Change:**
- `main.py`: merge `_on_hotkey_press` + `_on_hotkey_release` into a single `_on_hotkey_toggle`
- `main.py`: remove `_start_timeout`, `_cancel_timeout`, safety timers, min duration check (0.5s hardcode)
- `hotkey.py` / `hotkey_kglobalaccel.py`: remove hold-related dispatch logic

**Result:** Press once = start recording. Press again = stop, transcribe, inject.

---

## 2. Setup CLI (`setup.py`)

One-time setup script, run with `uv run python setup.py`. Writes results to the DB settings table. Can be re-run to change config.

### Phase 1 — llama-server binary

**Detection logic:**
```
nvidia-smi exits 0  → suggest CUDA build
rocm-smi exits 0    → suggest ROCm build
vulkaninfo exits 0  → suggest Vulkan build
fallback            → suggest CPU build
```

**Presented to user (all options shown, suggestion marked):**
```
Builds disponibles :
  [1] CPU         (universel, lent)
  [2] Vulkan      (GPU générique)
  [3] ROCm        (AMD)
  [4] CUDA        ← recommandé
  [5] Pointer vers un llama-server existant : ___
```

- Options 1–4: download from official llama.cpp GitHub releases (latest stable) into `~/.local/share/writher/llama/`
- Option 5: user provides path, WritHer uses it without managing its lifecycle (`managed=false`)

**DB settings written:**
- `llama_server_bin` → absolute path to binary
- `llama_server_managed` → `true` / `false`

### Phase 2 — Model

**VRAM detection:**
```python
nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits
rocm-smi --showmeminfo vram  # AMD fallback
# If neither: total_vram = 0 (CPU-only path)
```

**Budget:** `total_vram_mb * 0.55` (leaves ~45% free based on total, not current usage)

**Curated model tier list** (tool-calling capable, small footprint):

| Tier | Total VRAM | Model | VRAM req |
|------|-----------|-------|----------|
| CPU  | 0 (no GPU) | Qwen2.5-1.5B-Instruct Q4_K_M | ~1 GB RAM |
| S    | 4 GB | Qwen2.5-1.5B-Instruct Q4_K_M | ~1 GB |
| M    | 6 GB | Qwen2.5-3B-Instruct Q4_K_M | ~2.1 GB |
| L    | 8–10 GB | Qwen2.5-7B-Instruct Q4_K_M | ~4.7 GB |
| XL   | 12–16 GB | Qwen2.5-14B-Instruct Q4_K_M | ~8.5 GB |
| XXL  | 18 GB+ | Qwen2.5-14B-Instruct Q8_0 | ~14 GB |

Selection rule: pick the largest model where `vram_req ≤ budget`. Present recommendation, user can override or provide a custom `.gguf` path.

**Download:** via `huggingface-hub` CLI into `~/.local/share/writher/models/`

**DB settings written:**
- `llama_model` → absolute path to `.gguf`

---

## 3. `llm_manager.py` — Auto-load/Unload

New file. Single class `LlamaServerManager`. Replaces direct `llama-server` assumptions in `llm_backend.py`.

```
LlamaServerManager
  ensure_running()    # spawn if not running, poll /health (timeout 30s)
  shutdown()          # immediate kill
  _reset_timer()      # restart inactivity countdown
  _auto_shutdown()    # called by timer: kill + update tray state
```

**Lifecycle:**
```
First assistant call
  → ensure_running(): spawn process with bin + model from DB settings
  → poll GET /health until 200 (max 30s, else raise)
  → _reset_timer(timeout_sec)
  → tray = "LLM ready"

Each subsequent call
  → _reset_timer() (extends countdown)

Silence for timeout_sec
  → _auto_shutdown(): kill, tray = "LLM unloaded"

Next call after unload
  → ensure_running() respawns
```

**`managed` flag:**
- `true` (downloaded binary): Manager spawns and kills the process
- `false` (user-provided path): `ensure_running()` does health check only, never kills

**Timeout:** read from DB `llama_unload_timeout` (int seconds). Default 120.

**Tray states:** `idle` / `loading` / `ready` / `unloaded`

**Integration:** `assistant.py` calls `manager.ensure_running()` before each LLM call, `manager._reset_timer()` after.

---

## 4 & 5. Settings Window — Whisper + LLM

Two new sections added to `settings_window.py`.

### Whisper section
- Dropdown: `tiny | base | small | medium | large-v3`
- Label: "téléchargement auto au premier usage" (faster-whisper handles caching)
- On save: `save_setting("whisper_model", value)` → `main.py` recreates `Transcriber` instance

### LLM section
- **Model dropdown**: lists `.gguf` files found in `~/.local/share/writher/models/` + "Parcourir..." to pick any path
- **Unload timeout dropdown**: `60s | 120s | 300s | jamais (0)`
- On model change: if `LlamaServerManager` is active → shutdown, will respawn on next call
- On timeout change: `save_setting("llama_unload_timeout", value)` → manager reads on next timer reset

---

## Files Changed

| File | Change |
|------|--------|
| `main.py` | Toggle-only hotkey, integrate LlamaServerManager, hot-swap Transcriber |
| `hotkey.py` | Remove hold mode dispatch |
| `hotkey_kglobalaccel.py` | Remove hold mode dispatch |
| `settings_window.py` | Add Whisper + LLM sections |
| `database.py` | No schema change needed (settings KV already exists) |
| `llm_backend.py` | Remove direct server assumptions, delegate lifecycle to manager |
| `assistant.py` | Call `manager.ensure_running()` before LLM calls |
| `setup.py` | New file |
| `llm_manager.py` | New file |

---

## Out of Scope

- Streaming LLM / Whisper (separate initiative)
- VAD auto-stop
- TTS / wake word
- Conversation history
- Any UI redesign
