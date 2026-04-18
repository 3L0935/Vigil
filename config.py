from pynput.keyboard import Key

# ── Hotkeys ───────────────────────────────────────────────────────────────
# X11: pynput intercepts these directly.
# Wayland KDE: KGlobalAccel uses WAYLAND_HOTKEY / WAYLAND_ASSISTANT_HOTKEY instead
#              (modifier-only keys like AltGr/ctrl_r cannot be registered with KGlobalAccel).

# Press AltGr to toggle dictation (paste text directly)
HOTKEY = Key.alt_gr

# Press Ctrl+R to toggle assistant mode (notes, agenda, reminders)
ASSISTANT_HOTKEY = Key.ctrl_r

# Wayland KDE overrides (KGlobalAccel-compatible combos)
WAYLAND_HOTKEY = "Ctrl+Alt+W"
WAYLAND_ASSISTANT_HOTKEY = "Ctrl+Alt+R"

# String → pynput Key mapping for persisted X11 hotkey selection
_KEY_MAP = {
    "alt_gr":      Key.alt_gr,
    "ctrl_r":      Key.ctrl_r,
    "ctrl_l":      Key.ctrl_l,
    "alt_l":       Key.alt_l,
    "alt_r":       Key.alt_r,
    "scroll_lock": Key.scroll_lock,
    "pause":       Key.pause,
    "insert":      Key.insert,
    "home":        Key.home,
    "end":         Key.end,
}
_KEY_DISPLAY = list(_KEY_MAP)  # ordered list for UI dropdowns

# ── Language ──────────────────────────────────────────────────────────────
# Controls both Whisper transcription and all UI / assistant strings.
# Supported values: "en" (English), "it" (Italian), "fr" (French).
LANGUAGE = "en"   # first_run.py sets the real value; DB overrides at startup

# ── Whisper ───────────────────────────────────────────────────────────────
MODEL_SIZE = "base"
SAMPLE_RATE = 16000
DEVICE = "cpu"
COMPUTE_TYPE = "int8"

# ── llama-server (assistant) ─────────────────────────────────────────────
# llama-server exposes an OpenAI-compatible API at /v1/chat/completions.
# Same port as LMAgent-plus default (8080) for easy future integration.
LLAMA_SERVER_URL = "http://localhost:8080"
LLAMA_MODEL = "qwen2.5-7b-instruct"  # display default; runtime path comes from DB llama_model

# ── Obsidian vault (optional) ─────────────────────────────────────────────
# Set to your vault path to enable the search_obsidian_vault tool.
# Leave empty to disable the feature.
OBSIDIAN_VAULT_PATH = "/home/elo/.obsidian-vault/wiki/"

# ── Appointment notifications ─────────────────────────────────────────────
# How many minutes before an appointment to send a toast notification.
APPOINTMENT_REMIND_MINUTES = 15

# ── Overlay ───────────────────────────────────────────────────────────────
OVERLAY_POSITION = "bottom-center"   # {bottom,middle,top}-{left,center,right}
OVERLAY_SCREEN   = "auto"            # "auto" or xrandr output name e.g. "DP-2"
OVERLAY_ANSWER_TIMEOUT = 8           # seconds before answer card auto-closes

# ── TTS ───────────────────────────────────────────────────────────────────
TTS_ENGINE   = "off"      # "off" | "piper"
TTS_MODE     = "overlay"  # "off" | "overlay" | "tts" | "both"
TTS_VOICE_FR = ""
TTS_VOICE_EN = ""
