<p align="center">
  <img src="img/logo_writher.png" width="280" alt="WritHer">
</p>

<h1 align="center">WritHer Linux</h1>

<p align="center">
  <strong>Offline voice assistant &amp; dictation for Linux — dictate text anywhere.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Linux-FCC624?logo=linux&logoColor=black" alt="Linux">
  <img src="https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/STT-faster--whisper-orange" alt="faster-whisper">
  <img src="https://img.shields.io/badge/LLM-llama.cpp-blueviolet" alt="llama.cpp">
  <img src="https://img.shields.io/badge/TTS-Piper-teal" alt="Piper TTS">
  <img src="https://img.shields.io/badge/DE-KDE%20%7C%20GNOME-1d99f3" alt="KDE/GNOME">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
</p>

---

## What is WritHer?

WritHer sits in your system tray and gives you two modes:

| Mode | Default hotkey | What it does |
|---|---|---|
| **Dictation** | `Ctrl+Alt+W` | Transcribes your voice and pastes text directly into whichever app has focus — editors, browsers, chat windows, anything. |
| **Assistant** | `Ctrl+Alt+R` | Understands natural-language commands: save notes, schedule appointments, set reminders, search the web or your Obsidian vault — all by voice. |

Everything runs **locally**: speech recognition via [faster-whisper](https://github.com/SYSTRAN/faster-whisper), LLM via [llama.cpp](https://github.com/ggml-org/llama.cpp), optional TTS via [Piper](https://github.com/rhasspy/piper). No cloud, no API keys, no telemetry.

---

## Features

- **Toggle-mode dictation** — press once to start recording, press again to paste
- **Voice assistant** — notes, lists, appointments, reminders via natural speech
- **Web search** — ask the assistant to look something up; answer spoken aloud
- **Obsidian vault search** — query your markdown notes by voice
- **TTS (optional)** — [Piper](https://github.com/rhasspy/piper) voices (FR/EN), configurable mode: TTS only, overlay text only, or both
- **Animated overlay widget** — minimal pill-shaped overlay with expressive "Pandora" eyes reacting to state (listening, thinking, happy, error)
- **Full settings UI** — all configuration from the settings window; no editing config files
- **Multi-language** — English, French, Italian; add more via `locales.py`
- **X11 + Wayland** — global hotkeys via pynput (X11) or KGlobalAccel D-Bus (KDE Wayland)
- **Fully offline** after initial model download

---

## Requirements

- Linux (tested on KDE Plasma 6)
- Microphone
- `git` and `curl`
- Internet connection for first-run model download (~500 MB minimum)
- GPU required (CPU-only works; GPU strongly recommended for larger models)

---

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/3L0935/WritHer-Linux/main/install.sh -o /tmp/install-writher.sh && bash /tmp/install-writher.sh
```

Or, if you already have the repo cloned:

```bash
bash install.sh
```

The installer will:

1. Install [uv](https://docs.astral.sh/uv/) if not present
2. Set up the Python virtual environment and dependencies
3. Create a `writher` launcher in `~/.local/bin/`
4. Create a `.desktop` entry (app launcher + optional autostart)
5. Run the interactive first-run setup wizard

---

## First-run setup

The setup wizard handles everything interactively:

| Phase | What it does |
|---|---|
| **Language** | Choose EN / FR / IT |
| **llama-server** | Auto-detects GPU (CUDA / ROCm / Vulkan / CPU); downloads the matching llama.cpp binary from GitHub Releases |
| **LLM model** | Recommends a model tier based on available VRAM; downloads from Hugging Face (Qwen3.5 0.8B → 9B, or Mistral Small 24B) |
| **Whisper model** | Choose transcription size (tiny → large-v3) |
| **TTS (optional)** | Piper TTS: choose FR/EN voices and display mode |

If no configuration is detected at launch, WritHer automatically opens a terminal and runs the wizard.

---

## Usage

### Dictation

1. Focus any text field (editor, browser, chat…)
2. Press **`Ctrl+Alt+W`** — the overlay widget appears
3. Speak
4. Press **`Ctrl+Alt+W`** again — transcribed text is pasted automatically

### Assistant

1. Press **`Ctrl+Alt+R`** — overlay shows listening state
2. Speak a command
3. Press **`Ctrl+Alt+R`** again — answer appears in the overlay (and spoken aloud if TTS is on)

**Example commands (EN):**

- *"Search my notes for the API key for claude"*
- *"What is the weather in Paris?"*

**Example commands (FR):**

- *"Cherche dans mes notes le mot de passe Bitwarden"*
- *"Donne moi les nouveauté lié a anthropic AI sur claude"*


### System tray

Right-click the tray icon for:

- **Dictate / Assistant** — toggle buttons (useful on Wayland as hotkey fallback)
- **Stop TTS** — interrupt ongoing speech
- **Settings** — open the settings window
- **Quit**

---

## Settings

Open from the tray → **Settings**. All changes are saved to the local database on "Save".

| Section | What you can configure |
|---|---|
| Whisper model | tiny / base / small / medium / large-v3 |
| LLM model | Path to `.gguf` file (browse or type) |
| LLM unload timeout | Seconds of inactivity before the model is unloaded from RAM (0 = never) |
| LLM server URL | llama-server endpoint (default `http://localhost:8080`) |
| Obsidian vault | Path to your vault directory |
| Language | EN / FR / IT |
| Overlay position | 9-position grid (bottom-center default) |
| Lock to screen | Pin overlay to a specific monitor |
| Answer card timeout | Seconds before the answer pill auto-closes (5–30 s) |
| Hotkeys | Dictation and assistant key combos |
| TTS | Engine, voices (FR/EN), display mode, volume |
| Re-run setup | Launch the first-run wizard again (model swap, TTS setup, etc.) |
| Uninstall | Remove all WritHer data and desktop entries |

---

## Architecture

```
main.py                — entry point, pipeline workers, hotkey dispatch
config.py              — runtime constants (overridden by DB at startup)
setup_utils.py         — terminal detection, first-run detection
first_run.py           — interactive setup wizard (phases 0–3)
install.sh             — distro-agnostic installer
uninstall.sh           — data + desktop entry cleanup
hotkey.py              — HotkeyListener: X11 (pynput) / Wayland KDE (KGlobalAccel)
hotkey_kglobalaccel.py — KGlobalAccel D-Bus (Wayland KDE only)
platform_linux.py      — is_wayland() / is_x11()
recorder.py            — sounddevice audio capture
transcriber.py         — faster-whisper wrapper
injector.py            — pyperclip + pynput paste, clipboard save/restore
assistant.py           — LLM tool-calling: notes, appointments, reminders, search
llm_backend.py         — LlamaServerBackend (OpenAI-compatible /v1 API)
llm_manager.py         — llama-server process lifecycle management
obsidian.py            — Obsidian vault search (frontmatter + scoring)
notifier.py            — notify-send + ReminderScheduler
database.py            — SQLite: notes, appointments, reminders, settings KV
locales.py             — i18n strings (EN / FR / IT)
theme.py               — Pandora Blackboard colour palette + fonts
widget.py              — floating overlay (RecordingWidget + AnswerCard)
notes_window.py        — Notes / Agenda / Reminders viewer
settings_window.py     — full settings UI
tray_qt.py             — system tray (PyQt6, KDE Plasma)
brand.py               — tray icon + title bar image generation
```

---

## Hotkeys

Configurable from Settings. Default:

| Action | Default |
|---|---|
| Dictation | `Ctrl+Alt+W` |
| Assistant | `Ctrl+Alt+R` |

Format: `Ctrl+Alt+W`, `Meta+D`, `Shift+F9`, etc.

**X11:** uses pynput GlobalHotKeys — works on all X11 desktop environments.  
**Wayland KDE:** uses KGlobalAccel D-Bus — system-level, works even in Wayland-native apps. Falls back to pynput if KDE is not detected.  
**Wayland (non-KDE):** KGlobalAccel is unavailable; use the tray icon **Dictate / Assistant** buttons as fallback.

---

## Troubleshooting

**llama-server not reachable**  
The tray tooltip shows a warning at startup. llama-server is launched automatically by the process manager when needed. If it fails, check the log (`~/.local/share/writher/writher.log`) or re-run setup from Settings.

**Hotkey not detected (X11)**  
Some keyboard layouts map modifier keys differently. Check the app log for the registered combo.

**Hotkey not working (Wayland non-KDE)**  
KGlobalAccel is KDE-only. On GNOME Wayland, use the tray buttons instead.

**No audio / microphone not found**  
WritHer uses the system default input device. Check `pavucontrol` or `aplay -l`. The overlay displays an error message if the device can't be opened.

**TTS not playing**  
Requires Piper and voice files. Go to Settings → Re-run setup and select TTS at Phase 3. Voices can also be downloaded individually via Settings → TTS → More voices.

---

## Uninstall

**One-liner:**
```bash
curl -fsSL https://raw.githubusercontent.com/3L0935/WritHer-Linux/main/uninstall.sh | bash
```

**From the app:**  
Settings → Uninstall — removes data directory, desktop entries, and launcher.

**Manually (if you have the repo):**
```bash
bash uninstall.sh
```

The source directory is never removed automatically — delete it yourself if needed.

---

## License

MIT

---

<p align="center">
  <sub>Built with 🎙️ faster-whisper · 🧠 llama.cpp · 🗣️ Piper TTS · 🐍 Python</sub>
</p>
