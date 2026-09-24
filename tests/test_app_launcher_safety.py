from unittest.mock import Mock

import app_launcher


def test_close_never_uses_substring_process_match(monkeypatch):
    monkeypatch.setattr(app_launcher, '_find_app', lambda name: None)
    run = Mock(return_value=Mock(returncode=1))
    monkeypatch.setattr(app_launcher.subprocess, 'run', run)
    assert app_launcher.close('Firefox') == (False, 'Firefox')
    run.assert_called_once_with(['pkill', '-ix', 'firefox'], capture_output=True)


def test_unknown_multiword_target_cannot_kill_first_word(monkeypatch):
    monkeypatch.setattr(app_launcher, '_find_app', lambda name: None)
    run = Mock()
    monkeypatch.setattr(app_launcher.subprocess, 'run', run)
    assert app_launcher.close('Zen Browser') == (False, 'Zen Browser')
    run.assert_not_called()


def test_resolved_desktop_app_uses_exact_binary_only(monkeypatch):
    monkeypatch.setattr(app_launcher, '_find_app', lambda name: {
        'name': 'Zen Browser', 'exec': '/usr/bin/zen-browser %U'})
    run = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr(app_launcher.subprocess, 'run', run)
    assert app_launcher.close('Zen Browser') == (True, 'Zen Browser')
    run.assert_called_once_with(['pkill', '-ix', 'zen-browser'], capture_output=True)


def test_partial_app_name_does_not_inherit_a_different_binary(monkeypatch):
    monkeypatch.setattr(app_launcher, '_find_app', lambda name: {
        'name': 'Firefox Developer Edition', 'exec': '/usr/bin/firefox-developer-edition'})
    run = Mock(return_value=Mock(returncode=1))
    monkeypatch.setattr(app_launcher.subprocess, 'run', run)
    assert app_launcher.close('Firefox') == (False, 'Firefox')
    run.assert_called_once_with(['pkill', '-ix', 'firefox'], capture_output=True)


def test_shared_desktop_launcher_is_not_closed_by_process_name(monkeypatch):
    monkeypatch.setattr(app_launcher, '_find_app', lambda name: {
        'name': 'Example App', 'exec': 'flatpak run org.example.App'})
    run = Mock()
    monkeypatch.setattr(app_launcher.subprocess, 'run', run)
    assert app_launcher.close('Example App') == (False, 'Example App')
    run.assert_not_called()
