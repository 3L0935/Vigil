"""Draft-only state for the integrated Fold setup wizard."""

import threading
import os
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot
from PySide6.QtWidgets import QFileDialog

import config
import database as db
import locales
import tts
from logger import log

from .settings_schema import FIELDS
from .setup_service import MODEL_TIERS, SetupCancelled, detect_backend, recommended_model, prepare
from .assets import is_loopback_url, url_is_valid


_SETUP_ERRORS = {
    "Dictation and assistant shortcuts must differ": "setting_hotkeys_conflict",
    "Invalid Ollama endpoint": "privacy_bad_url",
    "Invalid llama-server endpoint": "privacy_bad_url",
    "Selected llama-server binary is not executable": "setup_binary_invalid",
    "Choose or enter an Ollama model": "setup_choose_ollama_model",
    "Cloud inference requires local mode to be disabled": "privacy_remote_blocked",
    "Remote inference is blocked by local mode": "privacy_remote_blocked",
    "Choose a GGUF file or a catalog model": "setup_choose_gguf",
    "Choose a voice for the selected language": "setup_choose_voice",
    "Piper is not installed": "setup_piper_missing",
    "Could not activate configuration": "setup_activation_failed",
}


class SetupModel(QObject):
    changed = Signal()
    prepared = Signal(object, str)
    progress = Signal(str)
    downloadProgress = Signal(str, int, int)
    finished = Signal(bool)
    cancelled = Signal(bool)
    ollamaReady = Signal(int, str, object)

    def __init__(self, translator, *, initial=False, parent=None):
        super().__init__(parent)
        self._translator = translator
        self._initial = initial
        self._page = 0
        self._busy = False
        self._ready = False
        self._status = ""
        self._download_done = 0
        self._download_total = 0
        self._cancel_event = threading.Event()
        self._prepared_values = None
        self._activate = None
        self._rollback_activation = None
        self._ollama_catalog = []
        self._ollama_request = 0
        from compositor import detect
        self._compositor = detect()
        self._requires_hotkey_consent = (
            os.environ.get("VIGIL_SKIP_HOTKEYS") != "1"
            and self._compositor in ("hyprland", "sway", "niri")
        )
        self._hotkey_consent = False
        self._original_language = translator.language
        self._draft = self._defaults()
        if not initial:
            self._load_saved_choices()
        self._draft["llama_backend"] = detect_backend()
        self.progress.connect(self._set_progress)
        self.downloadProgress.connect(self._set_download_progress)
        self.prepared.connect(self._receive_prepared)
        self.ollamaReady.connect(self._receive_ollama)

    def _defaults(self):
        values = {field.key: field.default for field in FIELDS if field.kind != "action"}
        values.update({
            "language": self._original_language,
            "whisper_model": "base",
            "whisper_language": self._original_language,
            "llama_model": "",
            "llama_catalog_model": recommended_model(),
            "llama_server_bin": "",
            "llama_server_managed": "false",
            "use_existing_binary": "false",
            "use_existing_model": "false",
            "llama_backend": detect_backend(),
            "tts_voice_fr": "",
            "tts_voice_en": "",
            "tts_mode": "overlay",
            "hotkey_dict": config.HOTKEY,
            "hotkey_assist": config.ASSISTANT_HOTKEY,
        })
        return values

    def _load_saved_choices(self):
        self._draft.update({key: db.get_setting(key, value)
                            for key, value in self._draft.items()
                            if key not in ("use_existing_binary", "use_existing_model", "llama_catalog_model")})
        binary = Path(self._draft["llama_server_bin"]).expanduser()
        if binary.is_file() and binary.stat().st_size and os.access(binary, os.X_OK):
            self._draft["use_existing_binary"] = "true"
        else:
            self._draft["llama_server_bin"] = ""
        model = Path(self._draft["llama_model"]).expanduser()
        if model.is_file() and model.suffix == ".gguf" and model.stat().st_size:
            self._draft["use_existing_model"] = "true"
        else:
            catalog_names = {tier[2] for tier in MODEL_TIERS}
            if model.name in catalog_names:
                self._draft["llama_catalog_model"] = model.name
            self._draft["llama_model"] = ""

    @Property(int, notify=changed)
    def page(self):
        return self._page

    @Property(bool, notify=changed)
    def busy(self):
        return self._busy

    @Property(bool, notify=changed)
    def ready(self):
        return self._ready

    @Property(str, notify=changed)
    def status(self):
        return self._status

    @Property(float, notify=changed)
    def progressValue(self):
        return min(1.0, self._download_done / self._download_total) if self._download_total else 0.0

    @Property(bool, notify=changed)
    def progressIndeterminate(self):
        return self._download_total <= 0

    @Property(bool, notify=changed)
    def initial(self):
        return self._initial

    @Property(bool, constant=True)
    def requiresHotkeyConsent(self):
        return self._requires_hotkey_consent

    @Property(bool, constant=True)
    def manualHotkeys(self):
        return self._compositor not in ("kde", "x11", "gnome", "hyprland", "sway", "niri")

    @Property(bool, notify=changed)
    def hotkeyConsent(self):
        return self._hotkey_consent

    @Slot(bool)
    def setHotkeyConsent(self, value):
        self._hotkey_consent = bool(value)
        self.changed.emit()

    def reopen(self):
        """Start a fresh reconfiguration draft without mutating active settings."""
        self._initial = False
        self._page = 0
        self._busy = False
        self._ready = False
        self._status = ""
        self._download_done = 0
        self._download_total = 0
        self._prepared_values = None
        self._ollama_catalog = []
        self._ollama_request += 1
        self._hotkey_consent = False
        self._original_language = self._translator.language
        self._draft = self._defaults()
        self._load_saved_choices()
        self.changed.emit()

    def set_activation_callbacks(self, activate, rollback):
        self._activate = activate
        self._rollback_activation = rollback

    @Slot(str, result=str)
    def value(self, key):
        return str(self._draft.get(key, ""))

    @Slot(str, str)
    def setValue(self, key, value):
        if self._busy:
            return
        self._draft[key] = str(value)
        if key in ("llm_provider", "ollama_cloud_url", "ollama_local_url", "ollama_api_key"):
            self._ollama_request += 1
            self._ollama_catalog = []
        if key == "language":
            self._translator.language = str(value)
        self.changed.emit()

    @Slot(result="QVariantList")
    def models(self):
        return [{"value": tier[2], "label": f"{tier[0]} · ~{tier[3]} MB"}
                for tier in MODEL_TIERS]

    @Slot(str, result="QVariantList")
    def voices(self, lang):
        return [{"value": "", "label": "—"}] + [
            {"value": voice, "label": voice} for voice in tts._BUILTIN_VOICES[lang]
        ]

    @Slot(result="QVariantList")
    def ollamaModels(self):
        chosen = self._draft.get("ollama_model", "")
        names = list(self._ollama_catalog)
        if chosen and chosen not in names:
            names.insert(0, chosen)
        return [{"value": name, "label": name} for name in names]

    @Slot()
    def refreshOllama(self):
        provider = self._draft["llm_provider"]
        url = self._draft["ollama_cloud_url" if provider == "ollama_cloud" else "ollama_local_url"]
        key = self._draft["ollama_api_key"] if provider == "ollama_cloud" else ""
        if not url_is_valid(url):
            self._status = self._translator.text("privacy_bad_url")
            self.changed.emit()
            return
        if self._draft["local_only"] == "true" and not is_loopback_url(url):
            self._status = self._translator.text("privacy_remote_blocked")
            self.changed.emit()
            return
        self._ollama_request += 1
        request_id = self._ollama_request
        self._status = self._translator.text("setting_fetching_models")
        self.changed.emit()

        def fetch():
            try:
                import httpx
                headers = {"Authorization": "Bearer " + key} if key else {}
                with httpx.Client(timeout=10, trust_env=False) as client:
                    response = client.get(url.rstrip("/") + "/api/tags", headers=headers)
                    response.raise_for_status()
                    names = [item["name"] for item in response.json().get("models", [])]
                result = (names, "")
            except Exception as exc:
                result = ([], type(exc).__name__)
            self.ollamaReady.emit(request_id, provider + "|" + url, result)

        threading.Thread(target=fetch, daemon=True, name="vigil-setup-ollama").start()

    @Slot(int, str, object)
    def _receive_ollama(self, request_id, source, result):
        provider = self._draft["llm_provider"]
        url = self._draft["ollama_cloud_url" if provider == "ollama_cloud" else "ollama_local_url"]
        if request_id != self._ollama_request or source != provider + "|" + url:
            return
        self._ollama_catalog, error = result
        self._status = (error or locales.translate("setting_models_available",
                             language=self._translator.language, count=len(self._ollama_catalog)))
        self.changed.emit()

    @Slot()
    def browseBinary(self):
        path, _ = QFileDialog.getOpenFileName(None, "llama-server")
        if path:
            self.setValue("llama_server_bin", path)
            self.setValue("llama_server_managed", "false")

    @Slot()
    def browseModel(self):
        path, _ = QFileDialog.getOpenFileName(None, "GGUF model", "", "GGUF (*.gguf)")
        if path:
            self.setValue("llama_model", path)

    @Slot()
    def back(self):
        if not self._busy and self._page > 0:
            self._page -= 1
            self.changed.emit()

    @Slot()
    def next(self):
        if self._busy:
            return
        if self._page == 5 and self._requires_hotkey_consent and not self._hotkey_consent:
            self._status = self._translator.text("setup_hotkey_consent_required")
            self.changed.emit()
            return
        if self._page < 6:
            self._page += 1
            self.changed.emit()
        elif self._page == 6:
            self.start_prepare()
        elif self._page == 7 and self._ready:
            previous = {key: db.get_setting(key, "") for key in self._prepared_values}
            try:
                db.save_settings(self._prepared_values)
                if self._activate and self._activate(self._initial) is False:
                    raise RuntimeError("Could not activate configuration")
            except Exception as exc:
                try:
                    db.save_settings(previous)
                    if self._rollback_activation:
                        self._rollback_activation(self._initial)
                except Exception as rollback_exc:
                    log.error("Setup rollback failed: %s", type(rollback_exc).__name__)
                    self._status = self._translator.text("setup_rollback_failed")
                else:
                    self._status = self._translator.text(_SETUP_ERRORS.get(str(exc), "setup_activation_failed"))
                self.changed.emit()
                return
            self.finished.emit(self._initial)

    @Slot()
    def resetDraft(self):
        if self._busy:
            return
        self._draft = self._defaults()
        self._translator.language = self._draft["language"]
        self.changed.emit()

    @Slot()
    def cancel(self):
        self._cancel_event.set()
        self._translator.language = self._original_language
        self.cancelled.emit(self._initial)

    @Slot(str)
    def _set_progress(self, message):
        key = {"binary": "setup_progress_binary", "model": "setup_progress_model",
               "voice fr": "setup_progress_voice_fr", "voice en": "setup_progress_voice_en"}.get(message)
        self._status = self._translator.text(key) if key else message
        self._download_done = 0
        self._download_total = 0
        self.changed.emit()

    @Slot(str, int, int)
    def _set_download_progress(self, stage, done, total):
        self._download_done = max(0, done)
        self._download_total = max(0, total)
        self.changed.emit()

    def start_prepare(self):
        self._busy = True
        self._cancel_event.clear()
        self._status = self._translator.text("setup_preparing")
        self.changed.emit()
        draft = dict(self._draft)
        last_progress = {}

        def publish_progress(stage, done, total):
            step = int(done * 100 / total) if total > 0 else done // (1024 * 1024)
            if last_progress.get(stage) != step:
                last_progress[stage] = step
                self.downloadProgress.emit(stage, done, total)

        def run():
            try:
                values = prepare(draft, self._cancel_event, self.progress.emit, publish_progress)
                self.prepared.emit(values, "")
            except SetupCancelled:
                self.prepared.emit({}, "cancelled")
            except Exception as exc:
                log.error("Setup preparation failed: %s", type(exc).__name__)
                self.prepared.emit({}, str(exc))

        threading.Thread(target=run, daemon=True, name="vigil-setup").start()

    @Slot(object, str)
    def _receive_prepared(self, values, error):
        if self._cancel_event.is_set():
            self._busy = False
            return
        if error:
            self._busy = False
            self._status = self._translator.text(_SETUP_ERRORS.get(error, "setup_prepare_failed"))
            self.changed.emit()
            return
        self._prepared_values = values
        self._busy = False
        self._ready = True
        self._page = 7
        self._status = ""
        self.changed.emit()
