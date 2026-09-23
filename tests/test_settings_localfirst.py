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


def test_dictation_fields_explain_input_format(model):
    settings, _ = model
    fields = {field["key"]: field for field in settings.fieldsFor("dictation")}
    assert fields["dictation_vocabulary"]["hintKey"] == "vocabulary_hint"
    assert fields["whisper_priming"]["hintKey"] == "priming_hint"


def test_invalid_vocabulary_prevents_batch_save(model):
    settings, _ = model
    settings.setValue("local_only", "false")
    settings.setValue("dictation_vocabulary", "invalid line")
    assert not settings.save()
    assert db.get_setting("local_only", "true") == "true"


def test_theme_changes_apply_to_all_windows_only_after_save(model):
    settings, _ = model
    theme = settings._theme
    settings.setValue("theme_accent_a", "#28cde0")
    settings.setValue("theme_accent_b", "#ed70de")
    settings.setValue("theme_background", "#201b29")
    settings.setValue("theme_surface", "#352b44")
    settings.setValue("theme_text", "#f8ecff")
    settings.setValue("theme_glass_opacity", "0.40")
    settings.setValue("theme_window_opacity", "0.65")
    settings.setValue("theme_gradient", "false")
    settings.setValue("theme_reduced_motion", "true")

    assert theme.accentA == "#6aafbe"
    assert theme.background == "#0a1019"
    assert settings.save()
    assert theme.background == "#201b29"
    assert theme.surface == "#352b44"
    assert theme.text == "#f8ecff"
    assert theme.glassOpacity == 0.4
    assert theme.windowOpacity == 0.65
    assert theme.accentA == "#28cde0"
    assert theme.accentB == "#ed70de"
    assert not theme.gradientEnabled
    assert theme.reducedMotion
    assert db.get_setting("theme_accent_a") == "#28cde0"
    assert db.get_setting("theme_gradient") == "false"
    assert db.get_setting("theme_background") == "#201b29"
    assert db.get_setting("theme_window_opacity") == "0.65"


def test_preset_changes_draft_palette_and_preserves_both_opacity_sliders(model):
    settings, _ = model
    assert [item["id"] for item in settings.themePresets()] == [
        "vigil", "classic_dark", "classic_light", "high_contrast"]
    settings.setValue("theme_glass_opacity", "0.40")
    settings.setValue("theme_window_opacity", "0.60")
    settings.applyThemePreset("classic_light")
    assert settings.themePreset() == "classic_light"
    assert settings.value("theme_background") == "#f2f4f7"
    assert settings.value("theme_glass_opacity") == "0.40"
    assert settings.value("theme_window_opacity") == "0.60"
    assert settings._theme.background == "#0a1019"
    settings.setValue("theme_accent_a", "#224488")
    assert settings.themePreset() == "custom"
    settings.applyThemePreset("classic_light")
    assert settings.save()
    assert settings._theme.background == "#f2f4f7"
    assert settings._theme.windowOpacity == 0.6
    assert db.get_setting("theme_glass_opacity") == "0.40"
    settings.resetTheme()
    assert settings.themePreset() == "vigil"
    assert settings.value("theme_window_opacity") == "1.00"
    assert settings._theme.background == "#f2f4f7"


def test_invalid_theme_color_cannot_be_saved(model):
    settings, _ = model
    settings.setValue("theme_accent_a", "not-a-color")
    assert settings.themePreviewColor("theme_accent_a") == "#6aafbe"
    assert not settings.save()
    assert db.get_setting("theme_accent_a", "") == ""


def test_failed_settings_activation_keeps_previous_theme(model):
    settings, _ = model
    settings._on_hotkey_change = Mock(return_value=False)
    settings.setValue("theme_accent_a", "#ff6633")
    assert not settings.save()
    assert settings._theme.accentA == "#6aafbe"
    assert db.get_setting("theme_accent_a", "") == ""


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
