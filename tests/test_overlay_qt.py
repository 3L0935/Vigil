"""Answer presentation keeps the existing hold and copy behavior."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from vigil_ui.overlay import OverlayModel


def test_answer_copy_uses_full_text_before_typewriter_finishes(monkeypatch):
    app = QApplication.instance() or QApplication([])
    overlay = OverlayModel()
    overlay.show_answer("A complete answer")
    assert overlay.answer == ""
    overlay.copyAnswer()
    assert app.clipboard().text() == "A complete answer"
    overlay.close()


def test_answer_countdown_holds_during_waiting_hover_and_tts(monkeypatch):
    QApplication.instance() or QApplication([])
    overlay = OverlayModel()
    overlay.show_answer("Answer")
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
    overlay._tick_answer()
    assert not overlay.hasAnswer
    overlay.close()
