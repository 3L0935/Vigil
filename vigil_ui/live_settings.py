"""Runtime services behind the Fold settings controls."""

import threading

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QFileDialog, QDialog, QListWidget, QPushButton, QVBoxLayout, QLabel, QProgressBar

import config
import database as db
import dictation
import locales
import privacy
import recovery
import tts
from logger import configure_content_logging, log, purge_logs

from .settings_model import SettingsModel
from .settings_schema import EDITABLE_KEYS, FIELDS
from .assets import download_voice, is_loopback_url, url_is_valid as _url_is_valid


_CONFIG_KEYS = {
    "whisper_model": "MODEL_SIZE",
    "language": "LANGUAGE",
    "overlay_position": "OVERLAY_POSITION",
    "overlay_screen": "OVERLAY_SCREEN",
    "tts_mode": "TTS_MODE",
    "tts_voice_fr": "TTS_VOICE_FR",
    "tts_voice_en": "TTS_VOICE_EN",
    "llm_provider": "LLM_PROVIDER",
    "llama_server_url": "LLAMA_SERVER_URL",
    "ollama_local_url": "OLLAMA_LOCAL_URL",
    "ollama_cloud_url": "OLLAMA_CLOUD_URL",
    "ollama_model": "OLLAMA_MODEL",
    "ollama_api_key": "OLLAMA_API_KEY",
    "assistant_name": "ASSISTANT_NAME",
    "obsidian_vault_path": "OBSIDIAN_VAULT_PATH",
    "hotkey_dict": "HOTKEY",
    "hotkey_assist": "ASSISTANT_HOTKEY",
}
_DB_ALIASES = {"hotkey_dict": "hotkey_dict", "hotkey_assist": "hotkey_assist"}


class LiveSettingsModel(SettingsModel):
    _ollamaReady = Signal(int, str, str, object)
    _voicesReady = Signal(str, int, object, str)
    _downloadReady = Signal(str, int, str, str)
    _downloadBytes = Signal(str, int, int, int)

    def __init__(self, translator, *, on_whisper_change=None,
                 on_hotkey_change=None, on_language_change=None,
                 on_redo_setup=None, parent=None):
        defaults = {field.key: field.default for field in FIELDS if field.key in EDITABLE_KEYS}
        values = {key: db.get_setting(_DB_ALIASES.get(key, key), default)
                  for key, default in defaults.items()}
        values["hotkey_dict"] = db.get_setting("hotkey_dict", config.HOTKEY)
        values["hotkey_assist"] = db.get_setting("hotkey_assist", config.ASSISTANT_HOTKEY)
        values["whisper_language"] = db.get_setting("whisper_language", values["language"])
        super().__init__(translator, initial=values, preview=False, parent=parent)
        self._on_whisper_change = on_whisper_change
        self._on_hotkey_change = on_hotkey_change
        self._on_language_change = on_language_change
        self._on_redo_setup = on_redo_setup
        self._request_id = 0
        self._voice_dialogs = {}
        self._voice_generation = {"fr": 0, "en": 0}
        self._ollamaReady.connect(self._receive_ollama)
        self._voicesReady.connect(self._receive_voices)
        self._downloadReady.connect(self._receive_download)
        self._downloadBytes.connect(self._receive_download_bytes)
        self.set_catalog("ollama_model", [values["ollama_model"]] if values["ollama_model"] else [])
        self.refresh_mics(show_status=False)
        self.refresh_screens()
        self.refresh_voices()

    def _text(self, key, **kwargs):
        return locales.translate(key, language=self._translator.language, **kwargs)

    def reload(self):
        """Read the active values after the setup wizard commits its draft."""
        for field in FIELDS:
            if field.key in EDITABLE_KEYS:
                self._values[field.key] = db.get_setting(field.key, field.default)
        self._revision += 1
        self.valuesChanged.emit()
        self.refresh_voices()

    def apply_immediate(self, key, value):
        if key == "whisper_model" and self._on_whisper_change:
            if self._on_whisper_change(value) is False:
                return False
        if key in _CONFIG_KEYS:
            setattr(config, _CONFIG_KEYS[key], value)
        db.save_setting(key, value)
        if key == "language" and self._on_language_change:
            self._on_language_change()
        elif key in ("tts_mode", "tts_volume", "tts_voice_fr", "tts_voice_en"):
            tts.init()
            if key.startswith("tts_voice_"):
                self.refresh_voices()
                self._revision += 1
                self.valuesChanged.emit()

    def speaker_count(self, lang):
        try:
            return tts.get_num_speakers(self._values.get("tts_voice_" + lang, ""))
        except Exception:
            return 1

    def refresh_mics(self, show_status=True):
        try:
            from recorder import input_devices
            names = [""] + input_devices()
            selected = self._values.get("mic_device", "")
            if selected and selected not in names:
                names.append(selected)
            self.set_catalog("mic_device", names)
            if show_status:
                self.set_status(self._text("mic_refresh_hint"))
        except Exception:
            self.set_catalog("mic_device", [""])
            self.set_status(self._text("mic_unavailable"))

    def refresh_screens(self):
        from PySide6.QtGui import QGuiApplication
        names = ["auto"] + [screen.name() for screen in QGuiApplication.screens()]
        selected = self._values.get("overlay_screen", "auto")
        if selected not in names:
            names.append(selected)
        self.set_catalog("overlay_screen", list(dict.fromkeys(names)))

    def refresh_voices(self):
        for lang in ("fr", "en"):
            names = [voice["name"] for voice in tts.list_piper_voices(lang)]
            selected = self._values.get("tts_voice_" + lang, "")
            if selected and selected not in names:
                names.insert(0, selected)
            self.set_catalog("tts_voice_" + lang, names)
            self.set_catalog("tts_speaker_" + lang,
                             [str(i) for i in range(max(1, self.speaker_count(lang)))])

    @Slot(result=bool)
    def save(self):
        values = dict(self._values)
        try:
            dictation.parse_vocabulary(values["dictation_vocabulary"])
        except ValueError as exc:
            self.set_status(self._text("vocabulary_invalid", line=str(exc)))
            return False
        if values["hotkey_dict"].strip() == values["hotkey_assist"].strip():
            self.set_status(self._text("setting_hotkeys_conflict"))
            return False
        if values["llm_provider"] == "ollama_cloud" and values["local_only"] == "true":
            self.set_status(self._text("privacy_remote_blocked"))
            return False
        selected_url = values["ollama_local_url"] if values["llm_provider"] == "ollama_local" else values["llama_server_url"]
        if values["local_only"] == "true" and values["llm_provider"] != "ollama_cloud" and not is_loopback_url(selected_url):
            self.set_status(self._text("privacy_remote_blocked"))
            return False
        urls = [values["llama_server_url"], values["ollama_local_url"],
                values["ollama_cloud_url"]]
        if any(url and not _url_is_valid(url) for url in urls):
            self.set_status(self._text("privacy_bad_url"))
            return False
        try:
            volume = float(values["tts_volume"])
            if not 0 <= volume <= 1:
                raise ValueError
            int(values["overlay_answer_timeout"])
        except ValueError:
            self.set_status(self._text("setting_invalid_value"))
            return False
        previous = {key: db.get_setting(key, "") for key in EDITABLE_KEYS}
        previous_config = {attr: getattr(config, attr) for attr in _CONFIG_KEYS.values()}
        previous_timeout = config.OVERLAY_ANSWER_TIMEOUT
        values["dictation_vocabulary"] = values["dictation_vocabulary"].strip()
        values["whisper_priming"] = values["whisper_priming"].strip()

        def rollback():
            db.save_settings(previous)
            for attr, value in previous_config.items():
                setattr(config, attr, value)
            config.OVERLAY_ANSWER_TIMEOUT = previous_timeout
            tts.init()
            if self._on_hotkey_change:
                self._on_hotkey_change()

        try:
            db.save_settings(values)
            for key, attr in _CONFIG_KEYS.items():
                setattr(config, attr, values[key])
            config.OVERLAY_ANSWER_TIMEOUT = int(values["overlay_answer_timeout"])
            configure_content_logging(privacy.enabled("log_content"))
            recovery.prune()
            if any(values[key] != previous[key] for key in
                   ("llm_provider", "llama_model", "llm_gpu_layers", "llama_ctx_size")):
                from llm_manager import manager
                manager.shutdown()
            import assistant
            assistant.reload_backend()
            tts.init()
            if self._on_hotkey_change and not self._on_hotkey_change():
                rollback()
                self.set_status(self._text("hotkey_rebind_failed"))
                return False
        except Exception as exc:
            log.error("Settings activation failed: %s", type(exc).__name__)
            try:
                rollback()
            except Exception as rollback_exc:
                log.error("Settings rollback failed: %s", type(rollback_exc).__name__)
            self.set_status(self._text("setting_save_failed"))
            return False
        self.set_status(self._text("setting_saved"))
        return True

    @Slot(str)
    def action(self, key):
        if key == "download_speech" and self._on_whisper_change:
            if self.downloadActive:
                return
            if self._on_whisper_change(self._values["whisper_model"], download=True):
                self.begin_download()
        elif key == "browse_llama_model":
            path, _ = QFileDialog.getOpenFileName(None, self._text("dialog_select_gguf"),
                                                  "", "GGUF (*.gguf)")
            if path:
                self.setValue("llama_model", path)
        elif key == "browse_vault":
            path = QFileDialog.getExistingDirectory(None, self._text("dialog_select_vault"))
            if path:
                self.setValue("obsidian_vault_path", path)
        elif key == "refresh_mics":
            self.refresh_mics()
        elif key == "refresh_ollama":
            self.refresh_ollama()
        elif key.startswith("preview_voice_"):
            lang = key[-2:]
            voice = self._values.get("tts_voice_" + lang, "")
            if voice:
                tts.preview(voice, int(self._values.get("tts_speaker_" + lang, "0")))
        elif key.startswith("more_voices_"):
            self.show_voice_library(key[-2:])
        elif key == "purge":
            from PySide6.QtWidgets import QMessageBox
            if QMessageBox.question(None, "Vigil", self._text("purge_confirm")) == QMessageBox.Yes:
                recovery.purge()
                purge_logs()
                self.set_status(self._text("purge_done"))
        elif key == "redo_setup" and self._on_redo_setup:
            self._on_redo_setup()
        elif key == "uninstall":
            import setup_utils
            setup_utils.launch_in_terminal(f'bash "{setup_utils.REPO_DIR / "uninstall.sh"}"')

    def refresh_ollama(self):
        provider = self._values["llm_provider"]
        url = self._values["ollama_local_url" if provider == "ollama_local" else "ollama_cloud_url"]
        key = self._values["ollama_api_key"] if provider == "ollama_cloud" else ""
        if not _url_is_valid(url):
            self.set_status(self._text("privacy_bad_url"))
            return
        if self._values["local_only"] == "true" and not is_loopback_url(url):
            self.set_status(self._text("privacy_remote_blocked"))
            return
        self._request_id += 1
        request_id = self._request_id
        self.set_status(self._text("setting_fetching_models"))

        def fetch():
            names = []
            error = ""
            try:
                import httpx
                headers = {"Authorization": "Bearer " + key} if key else {}
                with httpx.Client(timeout=10, trust_env=False) as client:
                    response = client.get(url.rstrip("/") + "/api/tags", headers=headers)
                    response.raise_for_status()
                    names = [item["name"] for item in response.json().get("models", [])]
            except Exception as exc:
                error = type(exc).__name__
            self._ollamaReady.emit(request_id, provider, url, (names, error))

        threading.Thread(target=fetch, daemon=True, name="vigil-ollama-catalog").start()

    @Slot()
    def invalidateRequests(self):
        self._request_id += 1

    @Slot(int, str, str, object)
    def _receive_ollama(self, request_id, provider, url, result):
        current_url = self._values["ollama_local_url" if provider == "ollama_local" else "ollama_cloud_url"]
        if request_id != self._request_id or provider != self._values["llm_provider"] or url != current_url:
            return
        names, error = result
        selected = self._values.get("ollama_model", "")
        if selected and selected not in names:
            names.insert(0, selected)
        self.set_catalog("ollama_model", names)
        self.set_status(self._text("setting_models_available", count=len(names)) if names
                        else self._text("setting_ollama_unreachable"))

    def show_voice_library(self, lang):
        self._voice_generation[lang] += 1
        generation = self._voice_generation[lang]
        dialog = QDialog()
        dialog.setWindowTitle(self._text("setting_voices_title") + " (" + lang.upper() + ")")
        dialog.resize(500, 420)
        dialog.setStyleSheet("""
            QDialog { background: #0e131d; color: #e1e5ed; }
            QLabel { color: #9ca6b7; }
            QListWidget { background: #111823; color: #e1e5ed;
                          border: 1px solid #27303e; border-radius: 6px; }
            QListWidget::item:selected { background: #354357; }
            QPushButton { background: #192231; color: #e1e5ed;
                          border: 1px solid #354357; border-radius: 6px;
                          min-height: 32px; }
            QPushButton:hover { background: #263141; }
        """)
        layout = QVBoxLayout(dialog)
        status = QLabel(self._text("setting_loading"))
        names = QListWidget()
        button = QPushButton(self._text("setting_download"))
        progress = QProgressBar()
        progress.setVisible(False)
        layout.addWidget(status)
        layout.addWidget(names)
        layout.addWidget(progress)
        layout.addWidget(button)
        button.clicked.connect(lambda: self._download_selected_voice(lang, generation, names, status))
        self._voice_dialogs[lang] = (dialog, names, status, progress)
        dialog.finished.connect(
            lambda: self._voice_dialogs.pop(lang, None)
            if self._voice_dialogs.get(lang, (None,))[0] is dialog else None
        )
        dialog.show()

        def fetch():
            try:
                voices = tts.fetch_piper_voices(lang)
                error = ""
            except Exception as exc:
                voices = []
                error = type(exc).__name__
            self._voicesReady.emit(lang, generation, voices, error)

        threading.Thread(target=fetch, daemon=True, name="vigil-voice-catalog").start()

    @Slot(str, int, object, str)
    def _receive_voices(self, lang, generation, voices, error):
        if generation != self._voice_generation[lang]:
            return
        view = self._voice_dialogs.get(lang)
        if not view:
            return
        _, names, status, _ = view
        names.clear()
        names.addItems([voice["name"] for voice in voices])
        status.setText(self._text("setting_voices_available", count=len(voices)) if not error
                       else self._text("setting_download_failed"))

    def _download_selected_voice(self, lang, generation, names, status):
        if self.downloadActive:
            return
        selected = names.currentItem()
        if not selected:
            return
        name = selected.text()
        status.setText(self._text("setting_loading"))
        view = self._voice_dialogs.get(lang)
        if view:
            view[3].setRange(0, 0)
            view[3].setVisible(True)
        self.begin_download()

        def fetch():
            error = ""
            try:
                download_voice(name, progress=lambda done, total:
                               self._downloadBytes.emit(lang, generation, done, total))
            except Exception as exc:
                error = type(exc).__name__
            self._downloadReady.emit(lang, generation, name, error)

        threading.Thread(target=fetch, daemon=True, name="vigil-voice-download").start()

    @Slot(str, int, int, int)
    def _receive_download_bytes(self, lang, generation, done, total):
        if generation != self._voice_generation[lang] or not self.downloadActive:
            return
        self.update_download(done, total)
        view = self._voice_dialogs.get(lang)
        if view:
            bar = view[3]
            bar.setRange(0, total if total > 0 else 0)
            if total > 0:
                bar.setValue(min(done, total))

    @Slot(str, int, str, str)
    def _receive_download(self, lang, generation, name, error):
        self.finish_download()
        if error:
            self.set_status(self._text("setting_download_failed"))
            return
        self.setValue("tts_voice_" + lang, name)
        self.refresh_voices()
        view = self._voice_dialogs.get(lang) if generation == self._voice_generation[lang] else None
        if view:
            view[0].accept()
