"""Answer presentation keeps the existing hold and copy behavior."""

import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import config
from vigil_ui.overlay import _TYPE_FRAME_MS, OverlayModel, reveal_step


def _reveal_seconds(length):
    return math.ceil(length / reveal_step(length)) * _TYPE_FRAME_MS / 1000


def test_a_normal_answer_streams_at_the_configured_pace():
    step = reveal_step(300)
    per_second = step / (_TYPE_FRAME_MS / 1000)
    assert 0.8 * config.OVERLAY_ANSWER_CPS <= per_second <= 1.3 * config.OVERLAY_ANSWER_CPS


def test_a_short_answer_does_not_crawl():
    assert _reveal_seconds(8) <= 0.15


def test_a_long_answer_stays_within_the_reveal_ceiling():
    for length in (500, 2000, 8000):
        assert _reveal_seconds(length) <= config.OVERLAY_ANSWER_REVEAL_MAX + 0.05


def test_reveal_step_never_falls_below_one_character():
    assert reveal_step(0) == 1
    assert reveal_step(1) == 1
    assert reveal_step(-5) == 1


def test_the_overlay_qml_compiles():
    """Guards the answer card against syntax and property errors that no
    Python test would otherwise see."""
    from pathlib import Path

    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    QApplication.instance() or QApplication([])
    path = (Path(__file__).resolve().parents[1]
            / "vigil_ui" / "qml" / "OverlayWindow.qml")
    engine = QQmlEngine()
    component = QQmlComponent(engine)
    component.setData(path.read_bytes(), QUrl.fromLocalFile(str(path)))
    assert [error.toString() for error in component.errors()] == []


def test_answer_copy_uses_full_text_before_typewriter_finishes(monkeypatch):
    app = QApplication.instance() or QApplication([])
    overlay = OverlayModel()
    overlay.show_answer("A complete answer")
    assert overlay.answer == ""
    overlay.copyAnswer()
    assert app.clipboard().text() == "A complete answer"
    overlay.close()


def test_preview_edit_copy_and_explicit_callbacks():
    app = QApplication.instance() or QApplication([])
    overlay = OverlayModel()
    calls = []
    overlay.set_preview_callbacks(lambda text: calls.append(('insert', text)),
                                  lambda: calls.append(('discard', None)),
                                  lambda text: calls.append(('vocabulary', text)))
    overlay.show_preview('raw')
    overlay.setPreviewText('edited')
    overlay.setPreviewText('é' * 33000)
    assert overlay.previewText == 'edited'
    overlay.copyPreview()
    assert app.clipboard().text() == 'edited'
    overlay.insertPreview()
    overlay.addPreviewVocabulary()
    overlay.discardPreview()
    assert calls == [('insert', 'edited'), ('vocabulary', 'edited'), ('discard', None)]
    overlay.close()


def test_answer_countdown_holds_during_waiting_hover_and_tts(monkeypatch):
    app = QApplication.instance() or QApplication([])
    clock = [100.0]
    monkeypatch.setattr(OverlayModel, "_now", lambda self: clock[0])
    overlay = OverlayModel()
    overlay.show_answer("Answer")
    while overlay._type_timer.isActive():
        overlay._type_next()
    overlay._deadline_ms = 100
    overlay.set_context_state(1, True)
    overlay._tick_answer()
    assert overlay.hasAnswer
    assert overlay._deadline_ms > 100
    overlay.set_context_state(0, False)
    overlay.setHover(True)
    overlay._deadline_ms = 100
    overlay._tick_answer()
    assert overlay.hasAnswer
    monkeypatch.setattr("tts.is_playing", lambda: True)
    overlay.setHover(False)
    overlay._deadline_ms = 100
    overlay._tick_answer()
    assert overlay.hasAnswer
    monkeypatch.setattr("tts.is_playing", lambda: False)
    overlay._deadline_ms = 100
    clock[0] += 0.1
    overlay._tick_answer()
    assert not overlay.hasAnswer
    overlay.close()


def test_answer_countdown_starts_after_typewriter_finishes(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("tts.is_playing", lambda: False)
    overlay = OverlayModel()
    overlay.show_answer("A" * 900)
    assert not overlay._answer_timer.isActive()

    for _ in range(10):
        overlay._type_next()
        overlay._tick_answer()
    # Still revealing: the countdown must not have started bleeding yet.
    assert overlay._type_timer.isActive()
    assert overlay.hasAnswer
    assert overlay._deadline_ms == 8000

    while overlay._type_timer.isActive():
        overlay._type_next()
    assert overlay.answer == "A" * 900
    assert overlay._answer_timer.isActive()
    assert overlay._deadline_ms == 8000
    overlay.close()


def test_hover_pauses_remaining_countdown(monkeypatch):
    app = QApplication.instance() or QApplication([])
    clock = [100.0]
    monkeypatch.setattr(OverlayModel, "_now", lambda self: clock[0])
    monkeypatch.setattr("tts.is_playing", lambda: False)
    overlay = OverlayModel()
    overlay.show_answer("Answer")
    while overlay._type_timer.isActive():
        overlay._type_next()
    overlay._deadline_ms = 500

    overlay.setHover(True)
    for _ in range(10):
        clock[0] += 0.1
        overlay._tick_answer()
    assert overlay._deadline_ms == 500
    assert overlay.hasAnswer

    overlay.setHover(False)
    for _ in range(4):
        clock[0] += 0.1
        overlay._tick_answer()
    assert overlay._deadline_ms == 100
    assert overlay.hasAnswer
    clock[0] += 0.1
    overlay._tick_answer()
    assert not overlay.hasAnswer
    overlay.close()


def test_visible_countdown_tracks_elapsed_time_and_restarts_for_new_answer(monkeypatch):
    app = QApplication.instance() or QApplication([])
    clock = [100.0]
    monkeypatch.setattr(OverlayModel, "_now", lambda self: clock[0])
    monkeypatch.setattr("tts.is_playing", lambda: False)
    overlay = OverlayModel()
    overlay.show_answer("First")
    assert overlay.answerCountdownState == "typing"
    assert overlay.answerSecondsRemaining == 8
    while overlay._type_timer.isActive():
        overlay._type_next()
    assert overlay.answerCountdownState == "counting"

    clock[0] += 2.2
    overlay._tick_answer()
    assert overlay.answerSecondsRemaining == 6
    assert 0.72 < overlay.answerProgress < 0.73

    overlay.show_answer("Next")
    assert overlay.answerCountdownState == "typing"
    assert overlay.answerSecondsRemaining == 8
    assert overlay.answerProgress == 1.0
    overlay.closeOverlay()
    assert overlay.answerCountdownState == "idle"
    assert not overlay._answer_timer.isActive()
    overlay.close()


def test_long_answer_reveal_is_bounded_without_truncation():
    app = QApplication.instance() or QApplication([])
    overlay = OverlayModel()
    text = 'A long answer. ' * 200
    overlay.show_answer(text)
    frames = 0
    while overlay._type_timer.isActive():
        overlay._type_next()
        frames += 1
        assert frames < 500, "the reveal is not bounded"
    assert overlay.answer == text
    assert not overlay._type_timer.isActive()
    assert overlay._answer_timer.isActive()
    assert frames * _TYPE_FRAME_MS / 1000 <= config.OVERLAY_ANSWER_REVEAL_MAX + 0.05
    overlay.close()
