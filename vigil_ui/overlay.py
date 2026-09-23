"""Qt Quick presentation adapter for recording and assistant responses."""

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

import config
import tts
from .screen import ActiveScreenTracker


class OverlayModel(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._window = None
        self._mode = "idle"
        self._message = ""
        self._answer = ""
        self._visible_answer = ""
        self._level = 0.0
        self._expression = "idle"
        self._waiting = False
        self._context_level = 0
        self._hover = False
        self._close_callback = None
        self._deadline_ms = 0
        self._message_timer = QTimer(self)
        self._message_timer.setSingleShot(True)
        self._message_timer.timeout.connect(self.hide)
        self._type_timer = QTimer(self)
        self._type_timer.setInterval(28)
        self._type_timer.timeout.connect(self._type_next)
        self._answer_timer = QTimer(self)
        self._answer_timer.setInterval(100)
        self._answer_timer.timeout.connect(self._tick_answer)
        self._screen_tracker = ActiveScreenTracker()
        self._screen_tracker.start()

    @Property(str, notify=changed)
    def mode(self):
        return self._mode

    @Property(str, notify=changed)
    def message(self):
        return self._message

    @Property(str, notify=changed)
    def answer(self):
        return self._visible_answer

    @Property(bool, notify=changed)
    def hasAnswer(self):
        return bool(self._answer)

    @Property(float, notify=changed)
    def level(self):
        return self._level

    @Property(str, notify=changed)
    def expression(self):
        return self._expression

    @Property(bool, notify=changed)
    def waiting(self):
        return self._waiting

    def attach_window(self, window):
        self._window = window

    def set_close_callback(self, callback):
        self._close_callback = callback

    def _show(self, mode, message=""):
        self._mode = mode
        self._message = message
        self.changed.emit()
        if self._window:
            self._position()
            self._window.show()

    def show_recording(self):
        self._message_timer.stop()
        self._show("recording")

    def show_assistant(self):
        self._message_timer.stop()
        self._show("assistant")

    def show_processing(self):
        self._message_timer.stop()
        self._show("processing")

    def show_status(self, text):
        self._message_timer.stop()
        self._show("status", text)

    def show_message(self, text, duration_ms=3000):
        self._show("message", text)
        self._message_timer.start(duration_ms)

    def show_answer(self, text):
        self._answer = text
        self._visible_answer = ""
        self._deadline_ms = max(1, int(config.OVERLAY_ANSWER_TIMEOUT * 1000))
        self._show("answer")
        self._type_timer.start()
        self._answer_timer.start()

    def _type_next(self):
        if len(self._visible_answer) >= len(self._answer):
            self._type_timer.stop()
            return
        self._visible_answer = self._answer[:len(self._visible_answer) + 3]
        self.changed.emit()

    def _tick_answer(self):
        if self._waiting or self._hover or tts.is_playing():
            self._deadline_ms = max(1, int(config.OVERLAY_ANSWER_TIMEOUT * 1000))
            return
        self._deadline_ms -= 100
        if self._deadline_ms <= 0:
            self.hide_answer()
            self.hide()

    @Slot(bool)
    def setHover(self, value):
        self._hover = value

    @Slot()
    def copyAnswer(self):
        QApplication.clipboard().setText(self._answer)

    @Slot()
    def closeOverlay(self):
        if self._close_callback:
            self._close_callback()
        self._waiting = False
        self._answer = ""
        self._visible_answer = ""
        self.hide()

    def hide_answer(self):
        if self._waiting:
            return
        self._answer = ""
        self._visible_answer = ""
        self._type_timer.stop()
        self._answer_timer.stop()
        self.changed.emit()

    def hide(self):
        if self._waiting and self._answer:
            return
        self._message_timer.stop()
        self._mode = "idle"
        self.changed.emit()
        if self._window:
            self._window.hide()

    def close(self):
        self._waiting = False
        self._answer = ""
        self._type_timer.stop()
        self._answer_timer.stop()
        if self._window:
            self._window.hide()

    def set_expression(self, expression):
        self._expression = expression
        self.changed.emit()

    def set_context_state(self, level, waiting):
        self._context_level = level
        self._waiting = waiting
        self.changed.emit()

    def update_level(self, level):
        # The recorder can run on PortAudio's thread. No Qt mutation there;
        # main.py samples this value on the UI timer.
        self._level = min(1.0, max(0.0, level))
        self.changed.emit()

    def _position(self):
        if not self._window:
            return
        screens = QGuiApplication.screens()
        selected = next((s for s in screens if s.name() == config.OVERLAY_SCREEN), None)
        if selected is None and config.OVERLAY_SCREEN == "auto":
            rect = self._screen_tracker.get_rect()
            if rect:
                cx, cy = rect[0] + rect[2] // 2, rect[1] + rect[3] // 2
                selected = next((screen for screen in screens
                                 if screen.geometry().contains(cx, cy)), None)
        if selected is None:
            selected = QGuiApplication.primaryScreen()
        if selected is None:
            return
        geometry = selected.availableGeometry()
        pos = config.OVERLAY_POSITION.split("-")
        vertical, horizontal = (pos[0], pos[-1]) if len(pos) > 1 else ("bottom", "center")
        margin = 18
        x = (geometry.left() + margin if horizontal == "left" else
             geometry.right() - self._window.width() - margin if horizontal == "right" else
             geometry.center().x() - self._window.width() // 2)
        y = (geometry.top() + margin if vertical == "top" else
             geometry.center().y() - self._window.height() // 2 if vertical == "middle" else
             geometry.bottom() - self._window.height() - margin)
        self._window.setScreen(selected)
        self._window.setPosition(x, y)
