# ── Hotkeys ───────────────────────────────────────────────────────────────
# Unified "Modifier+Key" format used on both X11 and Wayland.
# X11:    pynput GlobalHotKeys parses these at runtime.
# Wayland: KGlobalAccel D-Bus registers them dynamically.
# Examples: "Ctrl+Alt+W", "Ctrl+Shift+D", "Alt+F9"

HOTKEY           = "Ctrl+Alt+W"   # dictation
ASSISTANT_HOTKEY = "Ctrl+Alt+R"   # assistant

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

# ── Overlay ───────────────────────────────────────────────────────────────
OVERLAY_POSITION = "bottom-center"   # {bottom,middle,top}-{left,center,right}
OVERLAY_SCREEN   = "auto"            # "auto" or xrandr output name e.g. "DP-2"
OVERLAY_ANSWER_TIMEOUT = 8           # seconds before answer card auto-closes

# ── TTS ───────────────────────────────────────────────────────────────────
TTS_ENGINE   = "off"      # "off" | "piper"
TTS_MODE     = "overlay"  # "off" | "overlay" | "tts" | "both"
TTS_VOICE_FR = ""
TTS_VOICE_EN = ""
