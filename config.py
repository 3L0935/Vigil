# ── Hotkeys ───────────────────────────────────────────────────────────────
# Unified "Modifier+Key" format used on both X11 and Wayland.
# X11:    pynput GlobalHotKeys parses these at runtime.
# Wayland: KGlobalAccel D-Bus registers them dynamically.
# Examples: "Ctrl+Alt+W", "Ctrl+Shift+D", "Alt+F9"

HOTKEY           = "Ctrl+Alt+W"   # dictation
ASSISTANT_HOTKEY = "Ctrl+Alt+R"   # assistant

# ── Language ──────────────────────────────────────────────────────────────
# Controls UI / assistant strings. Recognition has its own saved language.
# Supported values: "en" (English), "it" (Italian), "fr" (French).
LANGUAGE = "en"   # integrated setup saves the real value; DB overrides at startup

# ── Whisper ───────────────────────────────────────────────────────────────
# Speech recognition backend. "faster_whisper" = CTranslate2 (CPU, or CUDA on
# NVIDIA). "whisper_cpp" = whisper.cpp, which reaches the GPU through Vulkan
# or ROCm; it keeps a whisper-server process warm so the model is not reloaded
# between dictations.
STT_BACKEND = "faster_whisper"
STT_GPU = False          # whisper.cpp only: run inference on the GPU
MODEL_SIZE = "base"
SAMPLE_RATE = 16000
DEVICE = "cpu"
COMPUTE_TYPE = "int8"

# ── LLM Provider ───────────────────────────────────────────────────────────
# "llama_cpp"    = llama-server local (managed or external)
# "ollama_local" = Ollama daemon local (http://localhost:11434, no auth)
# "ollama_cloud" = Ollama-compatible cloud API (URL + API key required)
LLM_PROVIDER = "llama_cpp"

# ── llama-server (assistant) ─────────────────────────────────────────────
# llama-server exposes an OpenAI-compatible API at /v1/chat/completions.
LLAMA_SERVER_URL = "http://localhost:8081"
LLAMA_MODEL = "qwen2.5-7b-instruct"  # display default; runtime path comes from DB llama_model

# ── Ollama defaults ────────────────────────────────────────────────────────
OLLAMA_LOCAL_URL = "http://localhost:11434"
OLLAMA_CLOUD_URL = "https://ollama.com"
OLLAMA_MODEL = ""  # runtime comes from DB ollama_model
OLLAMA_API_KEY = ""  # only used for ollama_cloud

# ── Assistant identity ────────────────────────────────────────────────────
ASSISTANT_NAME = "Vigil"
# Reply budget. It has to fit a conversational answer, not just a tool call:
# a command costs about eighty tokens, an explanation several hundred, and a
# reply that runs out of budget reaches the user as "I didn't understand".
# This model also reasons at length before answering, and that reasoning shares
# the budget, so a question with no matching tool can spend a thousand tokens
# thinking. Measured: at 512 a conversation is truncated most of the time, at
# 2048 it completes. The follow-up calls (repair, retry, synthesis) get less.
ASSISTANT_MAX_TOKENS = 2048
ASSISTANT_FOLLOWUP_TOKENS = 512

# ── Obsidian vault (optional) ─────────────────────────────────────────────
# Set to your vault path to enable the search_obsidian_vault tool.
# Leave empty to disable the feature.
OBSIDIAN_VAULT_PATH = ""

# ── Overlay ───────────────────────────────────────────────────────────────
OVERLAY_POSITION = "bottom-center"   # {bottom,middle,top}-{left,center,right}
OVERLAY_SCREEN   = "auto"            # "auto" or xrandr output name e.g. "DP-2"
OVERLAY_ANSWER_TIMEOUT = 8           # seconds before answer card auto-closes
# Answer reveal. The reply arrives complete from the model; it is streamed onto
# the card at a pace the eye can follow instead of appearing all at once.
# The pace is picked in the settings and OVERLAY_ANSWER_REVEAL_MAX caps how long
# the reveal may take, so a long answer speeds up rather than making the reader
# wait. Comfortable reading is roughly 20 characters per second. Clicking the
# card reveals the whole answer at once when the pace feels too slow.
OVERLAY_ANSWER_PACES = {"slow": 25, "normal": 45, "fast": 70}
OVERLAY_ANSWER_CPS = OVERLAY_ANSWER_PACES["normal"]
OVERLAY_ANSWER_REVEAL_MAX = 12      # seconds, reveal ceiling for any length

# ── TTS ───────────────────────────────────────────────────────────────────
TTS_ENGINE   = "off"      # "off" | "piper"
TTS_MODE     = "overlay"  # "off" | "overlay" | "tts" | "both"
TTS_VOICE_FR = ""
TTS_VOICE_EN = ""
