"""Exercise real Tk controls and their persisted settings when a display exists."""
import tkinter as tk
from unittest.mock import Mock

import pytest

import config
import database as db
from settings_window import SettingsWindow


@pytest.fixture
def window(monkeypatch, tmp_path):
    monkeypatch.setattr(db, '_DB_PATH', str(tmp_path / 'settings.db'))
    db.init()
    monkeypatch.setattr('recorder.input_devices', lambda: ['Synthetic USB microphone'])
    monkeypatch.setattr('tts.init', Mock())
    monkeypatch.setattr('assistant.reload_backend', Mock())
    monkeypatch.setattr('llm_manager.manager.shutdown', Mock())
    # Restore in-memory configuration after the actual Save callback changes it.
    for name in list(vars(config)):
        if name.isupper():
            monkeypatch.setattr(config, name, getattr(config, name))
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip('Tk display unavailable')
    root.withdraw()
    win = SettingsWindow(root, on_whisper_change=Mock(), on_hotkey_change=Mock())
    win._build()
    win._win.withdraw()
    root.update_idletasks()
    yield win
    root.destroy()


def test_actual_settings_save_independent_language_and_vocab(window):
    section = window._dictation_settings
    section.variables['whisper_language'].set('en')
    section.variables['mic_device'].set('Synthetic USB microphone')
    section.variables['max_record_seconds'].set('60')
    section.variables['local_only'].set(True)
    section.vocab.insert('1.0', 'roque aime = ROCm')
    section.priming.insert('1.0', 'Vigil, ROCm')
    window._lang_var.set('fr')
    window._save_linux_settings()
    assert db.get_setting('language') == 'fr'
    assert db.get_setting('whisper_language') == 'en'
    assert db.get_setting('dictation_vocabulary') == 'roque aime = ROCm'
    assert db.get_setting('mic_device') == 'Synthetic USB microphone'
    assert db.get_setting('max_record_seconds') == '60'
    assert db.get_setting('local_only') == 'true'
    assert db.get_setting('whisper_priming') == 'Vigil, ROCm'


def test_invalid_vocabulary_prevents_partial_settings_save(window, monkeypatch):
    error = Mock()
    monkeypatch.setattr('dictation_settings.messagebox.showerror', error)
    section = window._dictation_settings
    section.variables['local_only'].set(False)
    section.vocab.insert('1.0', 'invalid line')
    window._save_linux_settings()
    error.assert_called_once()
    assert db.get_setting('local_only', 'true') == 'true'


def test_explicit_download_callback_is_separate_from_selection(window):
    window._on_whisper_change('small', download=True)
    window._on_whisper_change_cb.assert_called_once_with('small', download=True)
