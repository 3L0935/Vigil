# WritHer — TTS (Text-to-Speech)

**Date:** 2026-04-17
**Status:** Approved

---

## Scope

Add optional local TTS to the assistant response pipeline. The user can choose between two engines (Piper or Kokoro), configure voices per language, and set a display mode (overlay only / TTS only / both). TTS is opt-in; the default is overlay only.

---

## Architecture

### Files Changed

| File | Change |
|------|--------|
| `tts.py` | New — engine abstraction + sounddevice playback |
| `first_run.py` | Add Phase 0 (language) + Phase 3 (TTS setup) |
| `settings_window.py` | Add TTS section (mode, voices, "more voices" dialog) |
| `main.py` | Call `tts.speak()` / `tts.stop()` in assistant pipeline |
| `config.py` | Change `LANGUAGE` default `"fr"` → `"en"` |

`database.py` — no schema change (KV settings table already exists).

### DB Settings

| Key | Values |
|-----|--------|
| `tts_engine` | `"piper"` / `"kokoro"` / `"off"` |
| `tts_mode` | `"off"` / `"overlay"` / `"tts"` / `"both"` |
| `tts_voice_fr` | voice name string |
| `tts_voice_en` | voice name string |

---

## 1. `tts.py`

### Public interface

```python
def init() -> None
    # Read tts_engine / tts_mode / tts_voice_fr / tts_voice_en from DB.
    # Load engine. No-op if tts_engine == "off".

def speak(text: str) -> None
    # Render text to audio, call sounddevice.play() (non-blocking).
    # Selects voice based on config.LANGUAGE.
    # No-op if tts_mode == "off".

def stop() -> None
    # sounddevice.stop() — immediate interrupt.

def is_enabled() -> bool
    # Returns tts_mode != "off".

def list_voices(lang: str) -> list[dict]
    # Returns locally available voices for lang ("fr" / "en").
    # Each dict: {"name": str, "engine": str, "path": str|None}

def fetch_voices(lang: str) -> list[dict]
    # Fetches full voice list from engine repo (network call).
    # Piper: parses https://huggingface.co/rhasspy/piper-voices/resolve/main/voices.json
    # Kokoro: introspects installed package for available voices.
```

### Piper backend

- Package: `piper-tts`
- Voice files: `~/.local/share/writher/tts/piper/{voice}.onnx` + `{voice}.onnx.json`
- Render: `PiperVoice.load(path).synthesize_stream_raw(text)` → bytes PCM → numpy int16
- Sample rate: 22050 Hz
- Built-in voice list:
  - FR: `fr_FR-siwis-medium`, `fr_FR-upmc-medium`, `fr_FR-mls-medium`
  - EN: `en_US-amy-medium`, `en_US-ryan-high`, `en_GB-alan-medium`

### Kokoro backend

- Package: `kokoro`
- All voices included at install (~300 MB total, no per-voice download)
- Render: `KPipeline(lang_code=...)(text, voice=voice_name)` → numpy float32 chunks → concatenate
- Sample rate: 24000 Hz
- Built-in voice list:
  - FR: `fr_0`, `fr_1`, `fr_2`
  - EN: `af_heart`, `af_bella`, `bm_george`

### Playback

```python
import sounddevice as sd
sd.play(audio_np, samplerate=sr)  # non-blocking
sd.stop()                          # interrupt
```

---

## 2. `first_run.py` — new phases

### Phase 0 — Language (added before existing phases)

```
Language / Langue :
  [1] English
  [2] Français
  [3] Italiano
```

Saves `save_setting("language", value)` + sets `config.LANGUAGE = value` immediately.
All subsequent first_run.py output stays in English regardless of choice.

### Phase 3 — TTS (new, appended after existing phases)

```
=== TTS (Text-to-Speech) ===

Choose a TTS engine, or skip:

  Piper TTS
    + Best French voice quality, ~50ms latency
    + Modular: download only voices you need (~80 MB/voice)
    - Requires downloading voice files separately

  Kokoro
    + Best English voice quality, all voices included
    + Single install (~300 MB total, no per-voice downloads)
    - French quality decent but not best-in-class

  [1] Piper TTS
  [2] Kokoro
  [3] No TTS (overlay only — skip)
```

If engine chosen:
1. Show FR voice list → user picks (or accepts default)
2. Show EN voice list → user picks (or accepts default)
3. Show mode: `[1] TTS only  [2] Overlay only  [3] Both`
4. If Piper: download selected voice `.onnx` + `.onnx.json` into `~/.local/share/writher/tts/piper/`
5. If Kokoro: `pip install kokoro` via `subprocess` (or instruct user to `uv add kokoro`)

If skipped: `save_setting("tts_engine", "off")`, `save_setting("tts_mode", "overlay")`.

Saves: `tts_engine`, `tts_mode`, `tts_voice_fr`, `tts_voice_en`.

---

## 3. `settings_window.py` — TTS section

New section added below existing LLM section:

```
─── TTS ──────────────────────────────────────────────────
Mode         [Off ▾]
Engine       Piper  (re-run first_run.py to change)
Voice (FR)   [fr_FR-siwis-medium ▾]   [More voices...]
Voice (EN)   [en_US-ryan-high ▾]      [More voices...]
──────────────────────────────────────────────────────────
```

- **Mode dropdown**: `Off / Overlay only / TTS only / Both`
- **Engine label**: read-only, shows current engine from DB
- **Voice dropdowns**: populated by `tts.list_voices(lang)` — shows installed voices only
- **"More voices..." button**: opens modal dialog
  - Calls `tts.fetch_voices(lang)` (network for Piper, local package introspection for Kokoro)
  - Displays list with `[Download]` button per voice (Piper: fetches `.onnx` + `.onnx.json` ; Kokoro: button says "Use" since voices are already in package)
  - On Piper download: saves files into `~/.local/share/writher/tts/piper/`
  - Refreshes dropdown after selection
- On save: `save_setting("tts_mode")`, `save_setting("tts_voice_fr")`, `save_setting("tts_voice_en")`, calls `tts.init()`

---

## 4. `main.py` changes

### `_load_settings()`

Add:
```python
tts_engine = db.get_setting("tts_engine", "off")
tts_mode   = db.get_setting("tts_mode", "overlay")
tts_voice_fr = db.get_setting("tts_voice_fr", "")
tts_voice_en = db.get_setting("tts_voice_en", "")
config.TTS_ENGINE   = tts_engine
config.TTS_MODE     = tts_mode
config.TTS_VOICE_FR = tts_voice_fr
config.TTS_VOICE_EN = tts_voice_en
```

Call `tts.init()` after `_load_settings()` in `main()`.

### `_assistant_worker`

After obtaining `result`:
```python
if tts.is_enabled():
    tts.speak(result)
if config.TTS_MODE in ("overlay", "both", "off"):
    widget.show_answer(result)
```

(`"off"` keeps current overlay behaviour so the app is usable without TTS configured.)

### `_on_hotkey_press` + `_on_assist_press`

Add `tts.stop()` as first line of each function.

---

## 5. `config.py` changes

- `LANGUAGE = "en"` (changed from `"fr"` — default to English until first_run.py sets it)
- Add:
  ```python
  TTS_ENGINE   = "off"
  TTS_MODE     = "overlay"
  TTS_VOICE_FR = ""
  TTS_VOICE_EN = ""
  ```

---

## Dependencies

Both engines are **optional extras** in `pyproject.toml`:

```toml
[project.optional-dependencies]
tts-piper  = ["piper-tts"]
tts-kokoro = ["kokoro"]
```

`first_run.py` installs the chosen extra by running:
```bash
uv sync --extra tts-piper   # or tts-kokoro
```

If TTS is skipped, no extra is installed.

Import is lazy-gated inside `tts.py`:
```python
if engine == "piper":
    from piper import PiperVoice
elif engine == "kokoro":
    from kokoro import KPipeline
```

`sounddevice` is already a runtime dependency.

---

## Out of Scope

- Streaming TTS (render-while-playing)
- Wake word detection
- Voice cloning
- TTS for notifications/reminders (assistant responses only)
- TTS language auto-detection (voice selection follows `config.LANGUAGE`)
