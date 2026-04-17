# WritHer Linux — CLAUDE.md

## Lancer l'app

```bash
uv run python main.py
```

Prérequis : `llama-server` tourner sur `http://localhost:8080` (ou URL configurée dans settings).

---

## Architecture

```
main.py              — entry point, pipeline workers (dictation + assistant), hotkey dispatch
config.py            — toutes les constantes runtime (hotkeys, LLM URL, vault path, langue)
hotkey.py            — HotkeyListener, dispatch X11 (pynput) / Wayland KDE (KGlobalAccel)
hotkey_kglobalaccel.py — KGlobalAccel D-Bus, Wayland KDE uniquement
platform_linux.py    — is_wayland() / is_x11()
recorder.py          — sounddevice capture, on_level callback pour le widget
transcriber.py       — faster-whisper wrapper
injector.py          — pyperclip + pynput paste, save/restore clipboard
assistant.py         — LLM tool-calling : notes, RDV, rappels, vault Obsidian
llm_backend.py       — LlamaServerBackend + fallback Hermes XML tool calls
obsidian.py          — recherche vault .md (frontmatter parsing + scoring)
notifier.py          — notify-send subprocess + ReminderScheduler (threading)
database.py          — SQLite : notes, appointments, reminders, settings KV
locales.py           — i18n fr/en/it
theme.py             — palette Pandora Blackboard (source of truth couleurs/fonts)
widget.py            — overlay recording (RecordingWidget, frameless Tk)
notes_window.py      — fenêtre notes/RDV/rappels (frameless Tk, overrideredirect)
settings_window.py   — fenêtre paramètres (frameless Tk, overrideredirect)
tray_qt.py           — system tray Qt/PySide6 (KDE Plasma)
brand.py             — génération logo/icône Pandora
```

---

## Gotchas critiques

### Glyphes Tkinter sur Linux
- **Tkinter n'a pas de font fallback** sur Linux.
- `✕` (U+2715, Dingbats) est **absent** de DejaVu Sans → rend invisible.
- Utiliser `×` (U+00D7, Latin-1) pour les croix de fermeture.
- Symptôme : bg hover change (rouge) mais texte invisible = toujours un problème de glyph.

### Pack ordering Tkinter
- `side="right"` doit être `pack()`-é **avant** `side="left"` dans le même parent.
- Wrapper les boutons fixes dans `tk.Frame(width=N)` + `pack_propagate(False)`.

### ctypes.windll
- Toujours sous `if sys.platform == "win32":` — `windll` n'existe pas sur Linux.

### KGlobalAccel D-Bus (Wayland)
- `flag=2` = `ActiveShortcut` (intercepté) — c'est ce qu'on veut.
- `flag=1` = `DefaultShortcut` — non intercepté au runtime.

### tool calls llama-server
- `arguments` dans les tool calls est une **string JSON** (pas un dict) → toujours `json.loads()`.

---

## Conventions UI

- Fenêtres frameless via `overrideredirect(True)` — titre bar, drag et close manuels.
- Toutes les couleurs/fonts dans `theme.py` — ne pas hardcoder ailleurs.
- `ctk.set_appearance_mode("dark")` appelé dans `main.py` avant toute fenêtre.

---

## État actuel (2026-04-17)

- MVP fonctionnel : dictée vocale, assistant LLM, notes/RDV/rappels, vault Obsidian search.
- Close buttons fonctionnels sur `settings_window` et `notes_window`.
- Hotkeys : X11 OK (AltGr dictée, Ctrl+R assistant), Wayland KDE via KGlobalAccel.
- Voir `TODO.md` pour la liste polish.
