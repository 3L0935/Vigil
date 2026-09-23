<p align="center">
  <img src="img/logo_vigil.png" alt="Vigil" width="100%">
</p>

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

## What is Vigil?

Vigil sits in your system tray and gives you two modes:

| Mode | Default hotkey | What it does |
|---|---|---|
| **Dictation** | `Ctrl+Alt+W` | Transcribes your voice and pastes text directly into whichever app has focus — editors, browsers, chat windows, anything. |
| **Assistant** | `Ctrl+Alt+R` | Understands natural-language commands: search the web, query your Obsidian vault, launch or close apps — all by voice. |

Vigil defaults to **strict local mode**: speech recognition via [faster-whisper](https://github.com/SYSTRAN/faster-whisper), inference through a loopback llama.cpp or Ollama server, and optional local Piper TTS. Remote inference and web tools are opt-in. Model and voice downloads are explicit actions; normal speech-model loading never contacts the network. No application telemetry.

---

## Features

- **Toggle-mode dictation** — press once to start recording, press again to paste
- **Voice assistant** — natural-language commands handled locally by the LLM
- **Web search (opt-in)** — enable network access and web tools in Settings, then ask the assistant to look something up
- **Obsidian vault search** — query your markdown notes by voice
- **App launcher** — open or close any installed app by name (searches `.desktop` files + PATH)
  - **Fuzzy matching** — phonetic approximations work ("dolfine" → Dolphin); single match auto-launches, multiple matches show a numbered list
  - **Multi-turn confirmation** — press the assistant hotkey again to reply with a number; answer card stays visible until resolved
- **Multi-turn context** — the assistant remembers the last 10 turns for up to 30 seconds; context level shown via Pandora eye color (white = fresh, progressively red = active context, yellow = waiting for reply)
- **Clear context** — say *"clear context"* / *"nettoie la conv"* to reset, or use the tray menu button
- **TTS (optional)** — [Piper](https://github.com/rhasspy/piper) voices (FR/EN), configurable mode: TTS only, overlay text only, or both
- **Animated overlay widget** — minimal pill-shaped overlay with expressive "Pandora" eyes reacting to state (listening, thinking, happy, error)
- **Full settings UI** — all configuration from the settings window; no editing config files
- **Multi-language** — English, French, Italian; add more via `locales.py`
- **X11 + universal Wayland hotkeys** — native binding on KDE (KGlobalAccel), GNOME (gsettings), Hyprland, Sway, niri; graceful manual-instructions fallback elsewhere
- **Strict local mode** — blocks remote inference/discovery and web tools by default
- **Personal vocabulary** — whole-word spoken → written replacements for dictation, plus recognition hints
- **Independent recognition language** — Auto / FR / EN / IT, separate from the interface
- **Microphone selection and retry** — refresh available inputs; failed captures can be retried without restarting
- **Bounded recording** — one shared session across shortcuts/tray, 120-second default limit; timeout audio is discarded
- **Clipboard preservation** — the fallback restores images, files and custom MIME formats; a newer copy wins
- **Private retained data** — content logging off by default; bounded failed-paste recovery and a purge button

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
curl -fsSL https://raw.githubusercontent.com/3L0935/Vigil/main/install.sh -o /tmp/install-vigil.sh && bash /tmp/install-vigil.sh
```

Or, if you already have the repo cloned:

```bash
bash install.sh
```

The installer will:

1. Install [uv](https://docs.astral.sh/uv/) if not present
2. Set up the Python virtual environment and dependencies
3. Create a `vigil` launcher in `~/.local/bin/`
4. Create a `.desktop` entry (app launcher)
5. Install Piper so the integrated wizard can offer spoken output

Launch `vigil` from the application menu or terminal. The Fold setup window opens on first launch.

---

## First-run setup

The Fold setup window handles configuration without opening a terminal:

| Phase | What it does |
|---|---|
| **Language** | Choose EN / FR / IT |
| **llama-server** | Auto-detects GPU (CUDA / ROCm / Vulkan / CPU); downloads the matching llama.cpp binary from GitHub Releases |
| **LLM model** | Recommends a model tier based on available VRAM; downloads from Hugging Face (Qwen3.5 0.8B → 9B, or Mistral Small 24B) |
| **Whisper model** | Choose transcription size (tiny → large-v3); download it explicitly from Settings if missing |
| **TTS (optional)** | Piper TTS: choose FR/EN voices and display mode |
| **Shortcuts** | Choose distinct dictation and assistant bindings |
| **Review** | Reuse installed files or download selected assets before saving |

Existing llama.cpp and Ollama configurations are reused. Settings → **Redo setup** opens the same window with the current choices prefilled. Cancel keeps active settings.

---

## Local mode and retained data

Settings → **Local mode and privacy** controls outbound access. Save to apply:

- **Strict local mode** is on by default, including upgrades. Only HTTP(S) endpoints on `localhost`, `127.0.0.0/8`, or `::1` are accepted for inference/discovery. Local requests ignore environment proxies and do not follow redirects. LAN servers require opting out of strict mode too.
- **Remote inference:** turn strict mode off, select a provider/URL and save. Spoken assistant commands are then sent to that server. Remote access does not automatically enable local tools.
- **Local tools with remote inference:** separately opt in to share note excerpts, file names, app results and conversation context. Without this permission, local tools are unavailable to the remote assistant and their execution is blocked. Provider/privacy changes reset conversation history.
- **Web tools:** separately enable web searches and website opening with strict mode off. Model/voice setup downloads are explicit exceptions. Vigil does not firewall applications launched through desktop shortcuts or files.

Dictation always transcribes locally. Inference remains CPU/int8 for speech; GPU backend changes are outside this release. **Selecting a speech model does not download it.** If missing or incomplete, Settings stays usable: choose **Download / repair selected speech model**. Loading/downloading runs in the background; capture is unavailable until ready. A corrupt cache produces an error instead of an implicit download.

Transcripts and assistant responses are excluded from logs by default. **Include transcripts and responses in logs** is an explicit troubleshooting option. Logs rotate at 1 MiB with three backups. Failed-paste recovery is plaintext in `$XDG_DATA_HOME/vigil/recovery_notes.txt` (normally `~/.local/share/vigil/`), capped at 1 MiB and retained for seven days by default. Choose 0/1/7/30 days; 0 disables recovery. Pruning runs at startup, when saving retention settings and on recovery writes. App data uses a private directory. **Clear logs and recovered dictations** removes retained logs/recovery while preserving settings and notes.

Old `recovery_notes.txt` files left beside the source by previous versions are not migrated or deleted automatically. System clipboard history is managed by your desktop, independently of Vigil's restoration.

## Dictation preferences

Settings → **Dictation** provides recognition language, microphone, recording limit, clipboard restoration delay, vocabulary and recognition hints. On upgrade, recognition initially retains the previous interface language; subsequent UI-language changes do not change it. Auto uses per-clip detection.

Vocabulary uses one `spoken = written` mapping per line, for example:

```text
roque aime = ROCm
vigil local = Vigil Local
```

Matching ignores case, respects whole words, prefers longer phrases and never recursively replaces its own output. Vocabulary applies only to dictation. Recognition hints such as `Vigil, ROCm, Obsidian` also help the assistant's speech recognition, but are best effort.

If a selected microphone disappears, Vigil reports it instead of choosing a different input silently. Reconnect it and refresh, or select another device; retry capture. Devices that reject 16 kHz are recorded at their native rate and resampled. PortAudio's device visibility depends on the audio backend; if a reconnected device still does not appear after refresh, restart Vigil. The default input follows the system selection at each recording.

A recording timeout **discards** the audio; it never pastes or executes it. Dictation and assistant cannot capture concurrently, and new capture waits for the current pipeline/model load to finish.

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

**What the assistant can do** (all triggered by voice, all multilingual):

| Capability | Example (EN) | Example (FR) |
|---|---|---|
| **Search the web** | *"What's the weather in Paris?"* | *"Donne-moi les news Anthropic"* |
| **Search Obsidian notes** | *"Search my notes for the Claude API key"* | *"Cherche dans mes notes le mot de passe Bitwarden"* |
| **Launch a desktop app** | *"Launch Firefox"* / *"Open Kitty"* | *"Lance Firefox"* / *"Ouvre Kitty"* |
| **Close a running app** | *"Close VLC"* / *"Quit Steam"* | *"Ferme VLC"* / *"Quitte Steam"* |
| **Open a website** | *"Open YouTube"* / *"Go to GitHub"* | *"Lance YouTube"* / *"Va sur Reddit"* |
| **Open a standard folder** | *"Open my Downloads"* | *"Ouvre mes téléchargements"* |
| **Find a file in a folder** | *"Find my CV in Downloads"* | *"Cherche mon CV dans téléchargements"* |
| **Open Vigil's settings** | *"Open settings"* | *"Ouvre les paramètres"* |
| **Reset conversation** | *"Clear context"* / *"Start over"* | *"Nettoie la conv"* / *"Repart à zéro"* |

**Smart routing:** the assistant distinguishes apps from websites from folders automatically — *"lance youtube"* opens the YouTube site (you don't need a YouTube app installed), *"lance Firefox"* launches the desktop browser, *"ouvre mes téléchargements"* opens the file manager.

**Web shortcuts** built-in (~50 sites): youtube, netflix, twitch, spotify, github, gitlab, gmail, outlook, twitter, x, instagram, reddit, tiktok, amazon, chatgpt, claude, gemini, wikipedia, drive, maps, discord, whatsapp, telegram, and more. Just say the name.

**Standard folders** recognised in any language: downloads/téléchargements/scaricati, documents/documenti, pictures/images/immagini, videos/vidéos, music/musique/musica, desktop/bureau/scrivania.

**File search** is fuzzy and multilingual — month names are expanded to digits in both directions (mars ↔ 03, march, marzo), plurals and minor spelling variants are handled (singular query matches plural folder names and vice versa), and dotted-name files like `2026.03.15.pdf` match a query mentioning *"march"* or *"mars"*. If the requested file doesn't exist, the assistant proposes similar files from the same folder and you reply with a number to open one.

**Fuzzy app matching:**

If the spoken name doesn't match exactly, the assistant tries phonetic approximations. If a single match is found, it auto-launches. If multiple apps match, a numbered list appears in the overlay:

```
Multiple apps found:
1: Dolphin
2: Dragon
Reply with the number.
```

Press the assistant hotkey again and say *"one"* / *"un"* / *"1"* / *"la première"* / *"second"* to confirm. The reply parser also handles common Whisper-FR misreads of "1" (`hein`, `han`) when the transcript is short. The overlay stays visible (yellow eyes) until you reply or click the close button.

The same multi-turn flow is used by the file-search results — *"ouvre la première"* opens the first match, *"ouvre la deuxième"* the second, etc.

**Multi-turn context:**

The Pandora eyes indicate context state:
- **White** — fresh context, no history
- **Progressively red** — active multi-turn context (1 → 3+ turns)
- **Yellow** — waiting for your numbered reply

Context resets automatically after 30 seconds of inactivity.


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
| Uninstall | Remove all Vigil data and desktop entries |

---

## Architecture

```
main.py                — entry point, pipeline workers, hotkey dispatch
config.py              — runtime constants (overridden by DB at startup)
setup_utils.py         — first-run detection and uninstall terminal helper
install.sh             — distro-agnostic installer
uninstall.sh           — data + desktop entry cleanup
compositor.py          — env-based compositor detection (KDE, GNOME, Hyprland, Sway, niri, wlr, X11)
hotkey/                — per-compositor adapters (base, kde, x11, gnome, hyprland, sway, niri, manual)
service.py             — D-Bus service exposing org.vigil.Service.Trigger(action)
vigil_trigger.py       — tiny CLI invoked by non-KDE compositor bindings (jeepney)
platform_linux.py      — is_wayland() / is_x11()
recorder.py            — sounddevice audio capture
transcriber.py         — faster-whisper wrapper
injector.py            — direct typing → MIME-preserving clipboard fallback → bounded recovery
clipboard_bridge.py    — clipboard transactions on the Qt GUI thread
privacy.py             — inference/discovery and tool permissions
recovery.py             — private bounded failed-paste recovery
dictation.py            — recognition settings and vocabulary
assistant.py           — LLM tool-calling: web search, vault search, app launcher, settings
llm_backend.py         — LlamaServerBackend (OpenAI-compatible /v1 API)
llm_manager.py         — llama-server process lifecycle management
obsidian.py            — Obsidian vault search (frontmatter + scoring)
url_shortcuts.py       — registry of ~50 popular sites (youtube, github, ...) + URL normaliser
folders.py             — XDG standard-folder resolver with multilingual aliases
file_search.py         — fuzzy recursive file search (month expansion, plural-tolerant matching)
database.py            — SQLite: settings KV store
locales.py             — i18n strings (EN / FR / IT)
tray_qt.py             — system tray (PySide6, KDE Plasma)
vigil_ui/              — Fold settings, overlay, setup wizard and runtime adapters
brand.py               — tray icon generation (Pandora eyes)
```

---

## Hotkeys

Configurable from Settings. Default:

| Action | Default |
|---|---|
| Dictation | `Ctrl+Alt+W` |
| Assistant | `Ctrl+Alt+R` |

Format: `Ctrl+Alt+W`, `Meta+D`, `Shift+F9`, etc.

### Compositor support

| Compositor | Mechanism | User burden |
|---|---|---|
| X11 (any WM) | pynput GlobalHotKeys | none |
| KDE Plasma 6 | KGlobalAccel D-Bus | none |
| GNOME Wayland | `gsettings` custom-keybindings | none (silent gsettings call) |
| Hyprland | managed block in `hyprland.conf` + `hyprctl reload` | consent in setup |
| Sway | managed block in `sway/config` + `swaymsg reload` | consent in setup |
| niri | managed block inside `config.kdl`'s `binds { }` + live-reload | consent in setup |
| wlroots / COSMIC / unknown | manual commands shown in setup | one-time config edit |

Non-KDE compositors execute `vigil-trigger <action>` on press; the CLI dials the D-Bus service (`org.vigil.Service.Trigger`) exposed by the running Vigil. Bindings live at the compositor level, so a temporary Vigil restart never loses them.

**KDE Plasma 6 Wayland note:** there's a long-standing KGlobalAccel quirk where the very first process to register a global shortcut in a fresh session gets the action descriptor accepted but never receives the Wayland keyboard grab — physical key presses bypass the app for the whole session. Vigil works around this transparently with a silent self-respawn on first launch of each session: it registers, cleanly releases, and re-execs itself from a fresh D-Bus client name so the grab installs correctly. You won't notice it (~2s extra startup once per session); your hotkeys just work after a reboot, no manual restart needed.

### CLI helpers

```bash
vigil --reconfigure-hotkeys   # rebind saved shortcuts after a WM switch or failed bind
vigil --uninstall-hotkeys     # remove every Vigil-managed binding
vigil-trigger dictate         # manual invocation (exit 1 if Vigil isn't running)
```

### Skip at install

For CI / headless installs, set `VIGIL_SKIP_HOTKEYS=1` before launching Vigil.

---

## Troubleshooting

**llama-server not reachable**
The tray tooltip shows a warning at startup. llama-server is launched automatically by the process manager when needed. If it fails, check the log (`~/.local/share/vigil/vigil.log`) or re-run setup from Settings.

**Hotkey not detected (X11)**
Some keyboard layouts map modifier keys differently. Check the app log for the registered combo.

**Hotkey not firing (any Wayland compositor)**
Run `vigil --reconfigure-hotkeys` — common after a compositor upgrade or WM switch. If you're on wlroots/COSMIC/labwc, Vigil prints the binding command at first-run; you need to add it to your compositor config manually and invoke `vigil-trigger dictate` / `vigil-trigger assistant` from there.

**No audio / microphone not found**
Select an input in Settings → Dictation, or keep the system default. Reconnect/refresh after a device disappears; the next capture retries opening it. Check `pavucontrol` for the system input.

**Dictation pastes nothing (Wayland)**
Vigil tries `wtype` first, then `xdotool`, then clipboard. Install at least one:
```bash
# Recommended (native Wayland, all apps)
sudo pacman -S wtype          # Arch / CachyOS
# OR fallback (XWayland apps only)
sudo pacman -S xdotool
```
On KDE Plasma, `wtype` may log `Compositor does not support the virtual keyboard protocol` — this is harmless; `xdotool` takes over automatically.

**TTS not playing**
Requires Piper and voice files. Go to Settings → Redo setup and select spoken output. Voices can also be downloaded individually via Settings → Speech output → More voices.

---

## Update

**One-liner:**
```bash
curl -fsSL https://raw.githubusercontent.com/3L0935/Vigil/main/update.sh | bash
```

**Or, if you have the repo cloned:**
```bash
bash update.sh
```

**Track a feature branch** — use `env` so the var applies to `bash`, not `curl`, and the syntax works in both bash and fish:
```bash
curl -fsSL https://raw.githubusercontent.com/3L0935/Vigil/<branch>/update.sh \
  | env VIGIL_BRANCH=<branch> bash
```

Stops the running instance, pulls the latest code, syncs dependencies, and restarts Vigil automatically. Your configuration and data are preserved.

---

## Uninstall

**One-liner:**
```bash
curl -fsSL https://raw.githubusercontent.com/3L0935/Vigil/main/uninstall.sh | bash
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

---

## Credits

Based on [WritHer](https://github.com/benmaster82/writher) by [@benmaster82](https://github.com/benmaster82).
