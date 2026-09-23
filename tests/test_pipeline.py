from unittest.mock import Mock

import numpy as np
import pytest

import main
from dictation_session import DictationSessions


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(main, 'widget', Mock())
    monkeypatch.setattr(main, 'tray', Mock())
    monkeypatch.setattr(main, 'root', Mock())
    monkeypatch.setattr(main, 'transcriber', Mock())
    monkeypatch.setattr(main.tts, 'stop', Mock())
    monkeypatch.setattr(main, '_shutting_down', False)
    main._pipeline_busy.clear()
    main._model_loading.clear()
    main._last_dictation.clear()
    main._dictation_sessions = DictationSessions()
    main._reinsert_armed = False
    main._skip_reinsert_release = False
    main._clear_preview_state()
    for q in [main._ui_actions, main._pipeline_queue, main._assistant_queue]:
        while not q.empty():
            q.get_nowait()


def test_sources_share_recorder_owner_and_failed_start_has_no_toggle_latch(app, monkeypatch):
    r = Mock(owner=None, recording=False)
    r.start.side_effect = [False, True]
    monkeypatch.setattr(main, 'recorder', r)
    main._toggle_recording('dictation')
    main._toggle_recording('dictation')
    assert r.start.call_count == 2
    assert not r.stop.called
    r.owner, r.recording = 'dictation', True
    r.stop.return_value = np.ones(100)
    main._tray_toggle_dictation()
    main._ui_actions.get_nowait()()
    r.stop.assert_called_once_with('dictation')
    assert main._pipeline_busy.is_set()
    assert not main._pipeline_queue.empty()


def test_other_mode_cannot_stop_active_recording(app, monkeypatch):
    r = Mock(owner='dictation', recording=True)
    monkeypatch.setattr(main, 'recorder', r)
    main._toggle_recording('assistant')
    r.stop.assert_not_called()
    r.start.assert_not_called()


def test_reinsert_waits_for_target_hotkey_and_swallows_release(app, monkeypatch):
    monkeypatch.setattr(main, 'recorder', Mock(recording=False, owner=None))
    paste = Mock(return_value='pasted')
    monkeypatch.setattr(main, 'inject', paste)
    main._last_dictation.store('raw text', 'Final text')
    monkeypatch.setattr(main.threading, 'Thread', lambda target, **kw: Mock(start=target))
    main._arm_reinsert_last()
    paste.assert_not_called()
    main._toggle_recording('dictation', from_hotkey=True)
    paste.assert_called_once_with('Final text')
    main._toggle_recording('dictation', from_hotkey=True, hotkey_release=True)
    main.recorder.start.assert_not_called()
    main._ui_actions.get_nowait()()
    assert not main._pipeline_busy.is_set()


def test_cancelled_transcription_cannot_inject_or_overwrite_last(app, monkeypatch):
    main._last_dictation.store('previous', 'Previous')
    session = main._dictation_sessions.start()
    assert main._dictation_sessions.queue(session)
    main._pipeline_busy.set()
    main.transcriber.transcribe.side_effect = lambda audio: (
        main._dictation_sessions.cancel(), 'late text')[1]
    paste = Mock()
    monkeypatch.setattr(main, 'inject', paste)
    main._pipeline_queue.put((session, np.ones(10)))
    main._pipeline_queue.put(main._STOP)
    main._dictation_worker()
    main._ui_actions.get_nowait()()
    paste.assert_not_called()
    assert main._last_dictation.get() == ('previous', 'Previous')
    assert not main._pipeline_busy.is_set()


def test_cancel_after_injection_starts_reports_too_late(app, monkeypatch):
    session = main._dictation_sessions.start()
    assert main._dictation_sessions.queue(session)
    main._pipeline_busy.set()
    main.transcriber.transcribe.return_value = 'hello'
    seen = []
    def paste(text):
        seen.append(main._dictation_sessions.cancel())
        return 'pasted'
    monkeypatch.setattr(main, 'inject', paste)
    main._pipeline_queue.put((session, np.ones(10)))
    main._pipeline_queue.put(main._STOP)
    main._dictation_worker()
    main._ui_actions.get_nowait()()
    assert seen == ['too_late']
    assert main._last_dictation.get() == ('hello', 'hello')


def test_preview_requires_explicit_insert_from_target_hotkey(app, monkeypatch):
    monkeypatch.setattr(main, 'recorder', Mock(recording=False, owner=None))
    monkeypatch.setattr(main.db, 'get_setting', lambda key, default='':
                        'true' if key == 'dictation_preview' else default)
    session = main._dictation_sessions.start()
    assert main._dictation_sessions.queue(session)
    main._pipeline_busy.set()
    main.transcriber.transcribe.return_value = 'raw phrase'
    paste = Mock(return_value='pasted')
    monkeypatch.setattr(main, 'inject', paste)
    main._pipeline_queue.put((session, np.ones(10)))
    main._pipeline_queue.put(main._STOP)
    main._dictation_worker()
    main._ui_actions.get_nowait()()
    paste.assert_not_called()
    main.widget.show_preview.assert_called_once_with('raw phrase')
    assert main._dictation_sessions.is_preview(session)
    main._arm_preview_insert('edited phrase')
    paste.assert_not_called()
    monkeypatch.setattr(main.threading, 'Thread', lambda target, **kw: Mock(start=target))
    main._toggle_recording('dictation', from_hotkey=True)
    main._toggle_recording('dictation', from_hotkey=True, hotkey_release=True)
    main._ui_actions.get_nowait()()
    paste.assert_called_once_with('edited phrase')
    assert main._last_dictation.get() == ('raw phrase', 'edited phrase')
    assert not main._pipeline_busy.is_set()


def test_discarded_preview_does_not_inject(app, monkeypatch):
    monkeypatch.setattr(main, 'recorder', Mock(recording=False, owner=None))
    session = main._dictation_sessions.start()
    assert main._dictation_sessions.queue(session)
    assert main._dictation_sessions.processing(session)
    assert main._dictation_sessions.preview(session)
    main._preview_session = session
    main._preview_raw = 'raw'
    paste = Mock()
    monkeypatch.setattr(main, 'inject', paste)
    main._discard_preview()
    assert not main._dictation_sessions.begin_injection(session)
    paste.assert_not_called()
    main.widget.hide_preview.assert_called_once()


def test_preview_vocabulary_requires_user_confirmation(app, monkeypatch):
    from PySide6.QtWidgets import QInputDialog, QMessageBox
    prompts = iter([('roque aime', True), ('ROCm', True)] * 2)
    monkeypatch.setattr(QInputDialog, 'getText', lambda *args: next(prompts))
    confirm = Mock(side_effect=[QMessageBox.No, QMessageBox.Yes])
    monkeypatch.setattr(QMessageBox, 'question', confirm)
    save = Mock()
    monkeypatch.setattr(main, 'settings_model', Mock())
    monkeypatch.setattr(main.db, 'get_setting', lambda key, default='': default)
    monkeypatch.setattr(main.db, 'save_setting', save)
    main._add_preview_vocabulary('preview text')
    save.assert_not_called()
    main._add_preview_vocabulary('preview text')
    save.assert_called_once_with('dictation_vocabulary', 'roque aime = ROCm')


def test_missing_model_leaves_controls_usable_and_next_load_can_succeed(app):
    main._model_loading.set()
    main._finish_model_load(None, 'missing model')
    assert main.transcriber is None
    assert not main._model_loading.is_set()
    main.widget.show_message.assert_called_with('missing model', 8000)
    model = Mock()
    main._finish_model_load(model, None)
    assert main.transcriber is model


def test_model_reload_refused_while_pipeline_uses_model(app):
    model = main.transcriber
    main._pipeline_busy.set()
    main._on_whisper_model_change('large-v3')
    assert main.transcriber is model
    assert not main._model_loading.is_set()


def test_model_load_failure_is_delivered_to_ui_without_blocking(app, monkeypatch):
    r = Mock(recording=False)
    monkeypatch.setattr(main, 'recorder', r)
    monkeypatch.setattr(main.db, 'save_setting', Mock())
    monkeypatch.setattr(main, 'Transcriber', Mock(side_effect=RuntimeError('missing')))
    monkeypatch.setattr(main.threading, 'Thread', lambda target, **kw: Mock(start=target))
    main._on_whisper_model_change('base')
    assert main._model_loading.is_set()
    main._ui_actions.get_nowait()()
    assert not main._model_loading.is_set()
    assert main.transcriber is None


def test_startup_migrates_recognition_language_and_applies_logging(app, monkeypatch):
    values = {'language':'fr', 'log_content':'true'}
    monkeypatch.setattr(main.db, 'get_setting', lambda key, default='': values.get(key,default))
    monkeypatch.setattr(main.db, 'save_setting', lambda key, value: values.__setitem__(key,value))
    configure = Mock()
    monkeypatch.setattr(main, 'configure_content_logging', configure)
    main._load_settings()
    assert values['whisper_language'] == 'fr'
    configure.assert_called_with(True)
    values['language'] = 'en'
    main._load_settings()
    assert values['whisper_language'] == 'fr'


def test_late_success_animation_does_not_hide_new_recording(app, monkeypatch):
    monkeypatch.setattr(main, 'recorder', Mock(recording=True))
    main._hide_if_idle()
    main.widget.hide.assert_not_called()


def test_late_success_animation_does_not_hide_answer(app, monkeypatch):
    monkeypatch.setattr(main, 'recorder', Mock(recording=False))
    main.widget.hasAnswer = True
    main._hide_if_idle()
    main.widget.hide.assert_not_called()


def test_main_event_loop_keeps_settings_available_after_model_failure(app, monkeypatch):
    from PySide6.QtCore import QObject
    import threading
    import database as db
    from pathlib import Path
    import tempfile

    temp = tempfile.TemporaryDirectory()
    monkeypatch.setattr(db, '_DB_PATH', str(Path(temp.name) / 'vigil.db'))
    monkeypatch.setattr(main.signal, 'signal', Mock())
    monkeypatch.setattr(main, 'TrayIcon', Mock())
    monkeypatch.setattr(main, 'Transcriber', Mock(side_effect=RuntimeError('missing model')))
    monkeypatch.setattr(main, 'HotkeyListener', Mock())
    monkeypatch.setattr(main.setup_utils, 'needs_first_run', lambda: False)
    monkeypatch.setattr(main.dbus_service, 'is_running', lambda: False)
    monkeypatch.setattr(main.dbus_service, 'start', lambda **kw: True)
    monkeypatch.setattr(main.injector, 'prewarm', Mock())
    monkeypatch.setattr(main.injector, 'check_deps', lambda: None)
    monkeypatch.setattr(main.clipboard_bridge, 'initialize', Mock())
    monkeypatch.setattr('hotkey.kde.preflight_grab_install', Mock())
    monkeypatch.setattr('recorder.input_devices', lambda: ['Synthetic microphone'])
    monkeypatch.setattr(main.tts, 'init', Mock())
    monkeypatch.setattr(main.sys, 'argv', ['vigil'])
    observed = []

    def check():
        if main._model_loading.is_set():
            main.QTimer.singleShot(50, check)
            return
        observed.append(main.transcriber is None and not main._model_loading.is_set())
        observed.append(main.settings_win.findChild(QObject, 'voiceModelsGroup') is not None)
        main.root.quit()

    threading.Timer(0.3, lambda: main._ui(check)).start()
    threading.Timer(4, lambda: main._ui(main.root.quit) if main.root else None).start()
    try:
        main.main()
        assert observed == [True, True]
    finally:
        main._pipeline_queue.put(main._STOP)
        main._assistant_queue.put(main._STOP)
        temp.cleanup()


def test_setup_cli_reopens_running_instance(monkeypatch):
    import vigil_trigger
    calls = []
    monkeypatch.setattr(main.sys, 'argv', ['vigil', '--setup'])
    monkeypatch.setattr(main.dbus_service, 'is_running', lambda: True)
    monkeypatch.setattr(vigil_trigger, 'trigger', lambda action: calls.append(action) or 0)
    with pytest.raises(SystemExit) as exit_info:
        main.main()
    assert exit_info.value.code == 0
    assert calls == ['setup']
