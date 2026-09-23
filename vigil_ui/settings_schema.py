"""Canonical editable settings exposed by the Fold UI.

Values are database strings. Presentation labels stay in ``locales``; the
schema never translates or changes the stored enum values.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    key: str
    group: str
    label: str
    kind: str = "text"
    default: str = ""
    options: tuple[str, ...] = ()
    provider: tuple[str, ...] = ()
    hint: str = ""


GROUPS = (
    ("voice", "group_voice_models"),
    ("general", "group_general"),
    ("dictation", "setting_dictation"),
    ("privacy", "setting_privacy"),
    ("overlay", "group_overlay"),
    ("theme", "group_theme"),
    ("speech", "group_speech_output"),
    ("maintenance", "group_maintenance"),
)

FIELDS = (
    Field("llm_provider", "voice", "setting_llm_provider", "choice", "llama_cpp",
          ("llama_cpp", "ollama_local", "ollama_cloud")),
    Field("whisper_model", "voice", "setting_whisper_model", "choice", "base",
          ("tiny", "base", "small", "medium", "large-v3")),
    Field("download_speech", "voice", "setting_download_speech", "action"),
    Field("llama_model", "voice", "setting_llm_model", provider=("llama_cpp",)),
    Field("browse_llama_model", "voice", "setting_browse", "action",
          provider=("llama_cpp",)),
    Field("llama_server_url", "voice", "setting_llm_url", "text",
          "http://localhost:8081", provider=("llama_cpp",)),
    Field("llama_unload_timeout", "voice", "setting_llm_unload", "choice", "120",
          ("60", "120", "300", "0"), provider=("llama_cpp",)),
    Field("llm_gpu_layers", "voice", "setting_llm_gpu_layers", "choice", "99",
          ("off", "10", "20", "33", "99"), provider=("llama_cpp",)),
    Field("llama_ctx_size", "voice", "setting_llm_ctx_size", "choice", "8192",
          ("2048", "4096", "8192", "16384", "32768"), provider=("llama_cpp",)),
    Field("ollama_local_url", "voice", "setting_ollama_url", "text",
          "http://localhost:11434", provider=("ollama_local",)),
    Field("ollama_cloud_url", "voice", "setting_ollama_url", "text",
          "https://ollama.com", provider=("ollama_cloud",)),
    Field("ollama_api_key", "voice", "setting_ollama_api_key", "secret",
          provider=("ollama_cloud",)),
    Field("ollama_model", "voice", "setting_ollama_model", "choice_editable",
          provider=("ollama_local", "ollama_cloud")),
    Field("refresh_ollama", "voice", "setting_refresh", "action",
          provider=("ollama_local", "ollama_cloud")),

    Field("assistant_name", "general", "setting_assistant_name", "text", "Vigil"),
    Field("language", "general", "setting_language", "choice", "en", ("en", "fr", "it")),
    Field("obsidian_vault_path", "general", "setting_obsidian_vault"),
    Field("browse_vault", "general", "setting_browse", "action"),
    Field("hotkey_dict", "general", "setting_hotkey_dict_hint", "text", "Ctrl+Alt+W"),
    Field("hotkey_assist", "general", "setting_hotkey_asst_hint", "text", "Ctrl+Alt+R"),

    Field("whisper_language", "dictation", "setting_whisper_language", "choice", "auto",
          ("auto", "en", "fr", "it")),
    Field("max_record_seconds", "dictation", "setting_max_record_seconds", "choice", "120",
          ("30", "60", "120", "300", "600")),
    Field("clipboard_restore_ms", "dictation", "setting_clipboard_restore_ms", "choice", "500",
          ("250", "500", "1000", "2000")),
    Field("mic_device", "dictation", "setting_mic_device", "choice", ""),
    Field("refresh_mics", "dictation", "setting_refresh_mics", "action"),
    Field("dictation_vocabulary", "dictation", "setting_vocabulary", "multiline",
          hint="vocabulary_hint"),
    Field("whisper_priming", "dictation", "setting_priming", "multiline",
          hint="priming_hint"),

    Field("local_only", "privacy", "setting_local_only", "toggle", "true"),
    Field("allow_web", "privacy", "setting_allow_web", "toggle", "false"),
    Field("share_local_data", "privacy", "setting_share_local_data", "toggle", "false"),
    Field("log_content", "privacy", "setting_log_content", "toggle", "false"),
    Field("recovery_days", "privacy", "setting_recovery_days", "choice", "7",
          ("0", "1", "7", "30")),
    Field("purge", "privacy", "setting_purge", "action"),

    Field("overlay_position", "overlay", "setting_overlay_position", "choice",
          "bottom-center", (
              "top-left", "top-center", "top-right", "middle-left", "middle-center",
              "middle-right", "bottom-left", "bottom-center", "bottom-right")),
    Field("overlay_screen", "overlay", "setting_overlay_screen", "choice", "auto"),
    Field("overlay_answer_timeout", "overlay", "setting_answer_timeout", "choice", "8",
          ("5", "8", "10", "15", "20", "30")),

    Field("theme_accent_a", "theme", "theme_accent_a", "color", "#6aafbe"),
    Field("theme_accent_b", "theme", "theme_accent_b", "color", "#a78bfa"),
    Field("theme_gradient", "theme", "theme_gradient", "toggle", "true"),
    Field("theme_reduced_motion", "theme", "theme_reduced_motion", "toggle", "false"),

    Field("tts_mode", "speech", "setting_tts_mode", "choice", "overlay",
          ("off", "overlay", "tts", "both")),
    Field("tts_voice_fr", "speech", "setting_tts_voice_fr", "choice"),
    Field("more_voices_fr", "speech", "setting_more_voices", "action"),
    Field("tts_speaker_fr", "speech", "setting_tts_speaker", "choice", "0"),
    Field("preview_voice_fr", "speech", "setting_tts_sample", "action"),
    Field("tts_voice_en", "speech", "setting_tts_voice_en", "choice"),
    Field("more_voices_en", "speech", "setting_more_voices", "action"),
    Field("tts_speaker_en", "speech", "setting_tts_speaker", "choice", "0"),
    Field("preview_voice_en", "speech", "setting_tts_sample", "action"),
    Field("tts_volume", "speech", "setting_tts_volume", "slider", "1.0"),

    Field("redo_setup", "maintenance", "setting_rerun_setup", "action"),
    Field("uninstall", "maintenance", "setting_uninstall", "action"),
)

BY_KEY = {field.key: field for field in FIELDS}
EDITABLE_KEYS = frozenset(field.key for field in FIELDS if field.kind != "action")
IMMEDIATE_KEYS = frozenset((
    "whisper_model", "language", "overlay_position", "overlay_screen",
    "llama_unload_timeout", "tts_mode", "tts_voice_fr", "tts_voice_en", "tts_volume",
))
