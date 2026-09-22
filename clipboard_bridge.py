"""Clipboard transactions on the existing Qt GUI thread, including MIME data."""
import threading
import uuid

from PySide6.QtCore import QObject, QMimeData, Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication

import database as db
from logger import log

_MARKER = 'application/x-vigil-paste-id'
_bridge = None


def clone_mime(source):
    result = QMimeData()
    if source is not None:
        for fmt in source.formats():
            result.setData(fmt, source.data(fmt))
        # Qt keeps images as a QVariant; the MIME byte representation can be empty.
        if source.hasImage():
            result.setImageData(source.imageData())
    return result


def _paste_keys():
    from pynput.keyboard import Controller, Key
    keyboard = Controller()
    with keyboard.pressed(Key.ctrl):
        keyboard.press('v')
        keyboard.release('v')


class ClipboardBridge(QObject):
    requested = Signal(object)

    def __init__(self, clipboard, paste_keys=_paste_keys):
        super().__init__()
        self.clipboard = clipboard
        self.paste_keys = paste_keys
        self.pending = None
        self.requested.connect(self._begin, Qt.ConnectionType.QueuedConnection)

    @Slot(object)
    def _begin(self, request):
        if request['cancelled'] or self.pending is not None:
            request['done'].set()
            return
        try:
            request['original'] = clone_mime(self.clipboard.mimeData())
            request['token'] = uuid.uuid4().bytes
            mime = QMimeData()
            mime.setText(request['text'])
            mime.setData(_MARKER, request['token'])
            self.pending = request
            self.clipboard.setMimeData(mime)
            QTimer.singleShot(80, lambda: self._paste(request))
        except Exception as exc:
            log.warning('Clipboard snapshot failed: %s', type(exc).__name__)
            self._restore(request)

    def _owns(self, request):
        current = self.clipboard.mimeData()
        return (current is not None and request.get('token') is not None
                and bytes(current.data(_MARKER)) == request['token']
                and current.text() == request['text'])

    def _paste(self, request):
        if self.pending is not request:
            return
        if request['cancelled'] or not self._owns(request):
            self._restore(request)
            return
        try:
            self.paste_keys()
            request['ok'] = True
        except Exception as exc:
            log.warning('Clipboard paste failed: %s', type(exc).__name__)
        try:
            delay = max(100, min(3000, int(db.get_setting('clipboard_restore_ms', '500'))))
        except ValueError:
            delay = 500
        QTimer.singleShot(delay, lambda: self._restore(request))

    def _restore(self, request):
        if self.pending is request:
            try:
                if self._owns(request):
                    self.clipboard.setMimeData(request['original'])
            except Exception as exc:
                log.warning('Clipboard restore failed: %s', type(exc).__name__)
            self.pending = None
        request['done'].set()

    def close(self):
        if self.pending:
            self.pending['cancelled'] = True
            self._restore(self.pending)

    def inject(self, text):
        request = {'text':text, 'done':threading.Event(), 'ok':False, 'cancelled':False}
        self.requested.emit(request)
        if not request['done'].wait(10):
            request['cancelled'] = True
        return request['ok']


def initialize():
    """Call once after tray.start(), from the Qt GUI thread."""
    global _bridge
    _bridge = ClipboardBridge(QApplication.clipboard())


def inject(text):
    return _bridge.inject(text) if _bridge else False


def close():
    if _bridge:
        _bridge.close()
