"""Settings remain local and are committed only after validation."""

import os
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

import config
import database as db
from vigil_ui.i18n import TranslationBridge
from vigil_ui.live_settings import LiveSettingsModel


@pytest.fixture
def model(monkeypatch, tmp_path):
    QApplication.instance() or QApplication([])
    monkeypatch.setattr(db, "_DB_PATH", str(tmp_path / "vigil.db"))
    db.init()
    monkeypatch.setattr("recorder.input_devices", lambda: ["Synthetic USB microphone"])
    monkeypatch.setattr("tts.init", Mock())
    monkeypatch.setattr("assistant.reload_backend", Mock())
    monkeypatch.setattr("llm_manager.manager.shutdown", Mock())
    for name in list(vars(config)):
        if name.isupper():
            monkeypatch.setattr(config, name, getattr(config, name))
    callback = Mock()
    settings = LiveSettingsModel(TranslationBridge("en"), on_whisper_change=callback)
    yield settings, callback


def test_save_independent_language_and_dictation_preferences(model):
    settings, _ = model
    settings.setValue("whisper_language", "en")
    settings.setValue("mic_device", "Synthetic USB microphone")
    settings.setValue("max_record_seconds", "60")
    settings.setValue("dictation_vocabulary", "roque aime = ROCm")
    settings.setValue("whisper_priming", "Vigil, ROCm")
    settings.setValue("language", "fr")
    assert settings.save()
    assert db.get_setting("language") == "fr"
    assert db.get_setting("whisper_language") == "en"
    assert db.get_setting("dictation_vocabulary") == "roque aime = ROCm"
    assert db.get_setting("mic_device") == "Synthetic USB microphone"
    assert db.get_setting("max_record_seconds") == "60"
    assert db.get_setting("whisper_priming") == "Vigil, ROCm"


def test_invalid_vocabulary_prevents_batch_save(model):
    settings, _ = model
    settings.setValue("local_only", "false")
    settings.setValue("dictation_vocabulary", "invalid line")
    assert not settings.save()
    assert db.get_setting("local_only", "true") == "true"


def test_download_is_an_explicit_action(model):
    settings, callback = model
    settings.setValue("whisper_model", "small")
    callback.assert_called_once_with("small")
    settings.action("download_speech")
    callback.assert_called_with("small", download=True)


def test_provider_fields_follow_draft_selection(model):
    settings, _ = model
    assert settings.fieldVisible("llama_model")
    assert not settings.fieldVisible("ollama_api_key")
    settings.setValue("llm_provider", "ollama_cloud")
    assert not settings.fieldVisible("llama_model")
    assert settings.fieldVisible("ollama_api_key")
