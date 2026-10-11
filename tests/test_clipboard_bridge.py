"""The paste keystroke has to be the one that actually reaches the window.

Measured on this machine: Qt's clipboard plus a pynput Ctrl+V reported success
and inserted nothing, while the same clipboard content pasted with
`xdotool key ctrl+v` arrived intact, accents included.
"""

import subprocess

import clipboard_bridge


def test_the_paste_key_goes_through_xdotool(monkeypatch):
    monkeypatch.setattr(clipboard_bridge.shutil, "which",
                        lambda name: "/usr/sbin/xdotool")
    calls = []
    monkeypatch.setattr(clipboard_bridge.subprocess, "run",
                        lambda cmd, **kwargs: calls.append(cmd))
    clipboard_bridge._paste_keys()
    assert calls == [["xdotool", "key", "--clearmodifiers", "ctrl+v"]]


def test_pynput_is_only_a_fallback(monkeypatch):
    monkeypatch.setattr(clipboard_bridge.shutil, "which", lambda name: None)
    used = []
    monkeypatch.setattr(clipboard_bridge, "_pynput_paste",
                        lambda: used.append("pynput") or True)
    clipboard_bridge._paste_keys()
    assert used == ["pynput"]


def test_a_failing_xdotool_falls_back_instead_of_raising(monkeypatch):
    monkeypatch.setattr(clipboard_bridge.shutil, "which",
                        lambda name: "/usr/sbin/xdotool")

    def fail(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(clipboard_bridge.subprocess, "run", fail)
    used = []
    monkeypatch.setattr(clipboard_bridge, "_pynput_paste",
                        lambda: used.append("pynput") or True)
    clipboard_bridge._paste_keys()
    assert used == ["pynput"]


def test_xdotool_success_does_not_double_paste(monkeypatch):
    monkeypatch.setattr(clipboard_bridge.shutil, "which",
                        lambda name: "/usr/sbin/xdotool")
    monkeypatch.setattr(clipboard_bridge.subprocess, "run",
                        lambda cmd, **kwargs: None)
    used = []
    monkeypatch.setattr(clipboard_bridge, "_pynput_paste",
                        lambda: used.append("pynput") or True)
    clipboard_bridge._paste_keys()
    assert used == []
