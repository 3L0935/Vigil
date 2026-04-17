from pynput.keyboard import Key

# ── Hotkeys ───────────────────────────────────────────────────────────────
# Hold AltGr to dictate (paste text directly)
HOTKEY = Key.alt_gr

# Hold Ctrl+R to activate assistant mode (notes, agenda, reminders)
ASSISTANT_HOTKEY = Key.ctrl_r

# ── Language ──────────────────────────────────────────────────────────────
# Controls both Whisper transcription and all UI / assistant strings.
# Supported values: "en" (English), "it" (Italian), "fr" (French).
LANGUAGE = "fr"

# ── Whisper ───────────────────────────────────────────────────────────────
MODEL_SIZE = "base"
SAMPLE_RATE = 16000
DEVICE = "cpu"
COMPUTE_TYPE = "int8"

# ── llama-server (assistant) ─────────────────────────────────────────────
# llama-server exposes an OpenAI-compatible API at /v1/chat/completions.
# Same port as LMAgent-plus default (8080) for easy future integration.
LLAMA_SERVER_URL = "http://localhost:8080"
LLAMA_MODEL = "qwen2.5-7b-instruct"  # strong tool-calling support

# ── Obsidian vault (optional) ─────────────────────────────────────────────
# Set to your vault path to enable the search_obsidian_vault tool.
# Leave empty to disable the feature.
OBSIDIAN_VAULT_PATH = "/home/elo/.obsidian-vault/wiki/"

# ── Recording mode ────────────────────────────────────────────────────────
# True = hold key to record (release stops).  False = toggle (press start, press stop).
HOLD_TO_RECORD = True

# Maximum recording duration in seconds (toggle mode only, safety net).
MAX_RECORD_SECONDS = 120

# ── Appointment notifications ─────────────────────────────────────────────
# How many minutes before an appointment to send a toast notification.
APPOINTMENT_REMIND_MINUTES = 15
