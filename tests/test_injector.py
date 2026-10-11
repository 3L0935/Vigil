"""Injection must carry accented characters, or fail loudly rather than mangle.

On KWin there is no virtual keyboard protocol, so wtype cannot work and the
clipboard is the only path that keeps "plutôt" intact. Typing through xdotool
drops what the layout cannot produce, silently.
"""

import subprocess
from unittest.mock import Mock

import pytest

import injector


@pytest.fixture(autouse=True)
def wayland_and_clean_cache(monkeypatch):
    monkeypatch.setattr(injector, "is_wayland", lambda: True)
    monkeypatch.setattr(injector, "_wtype_unsupported", False)
    monkeypatch.setattr(injector.shutil, "which", lambda name: "/usr/sbin/" + name)


@pytest.fixture
def methods(monkeypatch):
    """Record which injection path runs, in order."""
    calls = []
    results = {"wtype": False, "clipboard": True, "xdotool": True, "recovery": True}

    def record(name):
        def run(text):
            calls.append(name)
            return results[name]
        return run

    monkeypatch.setattr(injector, "_inject_wtype", record("wtype"))
    monkeypatch.setattr(injector, "_inject_clipboard", record("clipboard"))
    monkeypatch.setattr(injector, "_inject_xdotool", record("xdotool"))
    import recovery
    monkeypatch.setattr(recovery, "save", lambda text: results["recovery"])
    return calls, results


ACCENTED = "Je vois déjà qu'il faudrait peut-être fixer ça, plutôt."
ASCII = "plain ascii text"


def test_the_clipboard_carries_accents_before_xdotool_is_considered(methods):
    calls, _ = methods
    assert injector.inject(ACCENTED) == "pasted"
    assert calls == ["wtype", "clipboard"]


def test_wtype_still_wins_when_the_compositor_supports_it(methods):
    calls, results = methods
    results["wtype"] = True
    assert injector.inject(ACCENTED) == "pasted"
    assert calls == ["wtype"]


def test_xdotool_is_never_given_accented_text(methods):
    calls, results = methods
    results["clipboard"] = False
    assert injector.inject(ACCENTED) == "recovered"
    assert "xdotool" not in calls


def test_ascii_may_fall_back_to_xdotool(methods):
    calls, results = methods
    results["clipboard"] = False
    assert injector.inject(ASCII) == "pasted"
    assert calls == ["wtype", "clipboard", "xdotool"]


def test_ascii_prefers_the_clipboard_too(methods):
    calls, _ = methods
    assert injector.inject(ASCII) == "pasted"
    assert calls == ["wtype", "clipboard"]


def test_empty_text_fails_without_trying_anything(methods):
    calls, _ = methods
    assert injector.inject("") == "failed"
    assert calls == []


def test_unsupported_compositor_is_remembered(monkeypatch):
    error = subprocess.CalledProcessError(1, "wtype", stderr=(
        "Compositor does not support the virtual keyboard protocol\n"))
    attempts = []

    def fail(cmd, **kwargs):
        attempts.append(cmd)
        raise error

    monkeypatch.setattr(injector.subprocess, "run", fail)
    assert injector._inject_wtype(ACCENTED) is False
    assert injector._wtype_unsupported is True
    # Second call must not spawn wtype again.
    assert injector._inject_wtype(ACCENTED) is False
    assert len(attempts) == 1


def test_other_wtype_failures_are_retried(monkeypatch):
    attempts = []

    def fail(cmd, **kwargs):
        attempts.append(cmd)
        raise subprocess.CalledProcessError(1, "wtype", stderr="something else")

    monkeypatch.setattr(injector.subprocess, "run", fail)
    assert injector._inject_wtype(ACCENTED) is False
    assert injector._inject_wtype(ACCENTED) is False
    assert len(attempts) == 2
    assert injector._wtype_unsupported is False


def test_a_missing_wtype_is_not_an_error(monkeypatch):
    monkeypatch.setattr(injector.shutil, "which", lambda name: None)
    assert injector._inject_wtype(ACCENTED) is False


def test_x11_never_tries_wtype(monkeypatch):
    monkeypatch.setattr(injector, "is_wayland", lambda: False)
    called = []
    monkeypatch.setattr(injector.subprocess, "run", lambda *a, **k: called.append(1))
    assert injector._inject_wtype(ACCENTED) is False
    assert called == []


def test_ascii_predicate():
    assert injector._is_ascii(ASCII)
    assert not injector._is_ascii("déjà")


def test_prewarm_falls_through_to_a_working_tool(monkeypatch):
    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd[0])
        return Mock(returncode=1 if cmd[0] == "wtype" else 0)

    monkeypatch.setattr(injector.subprocess, "run", run)
    injector.prewarm()
    assert calls == ["wtype", "xdotool"]


def test_prewarm_stops_at_the_first_tool_that_answers(monkeypatch):
    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd[0])
        return Mock(returncode=0)

    monkeypatch.setattr(injector.subprocess, "run", run)
    injector.prewarm()
    assert calls == ["wtype"]
