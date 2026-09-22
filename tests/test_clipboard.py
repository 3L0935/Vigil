import threading
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QMimeData
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from clipboard_bridge import ClipboardBridge, clone_mime


@pytest.fixture(scope='module')
def qt():
    app = QApplication.instance() or QApplication([])
    yield app


class FakeClipboard:
    def __init__(self, mime):
        self.mime = mime
    def mimeData(self):
        return self.mime
    def setMimeData(self, mime):
        self.mime = mime


def transaction(qt):
    original = QMimeData()
    original.setData('text/uri-list', b'file:///tmp/example.txt\r\n')
    original.setData('image/png', b'synthetic image bytes')
    original.setData('application/custom', b'custom data')
    clip = FakeClipboard(original)
    bridge = ClipboardBridge(clip, Mock())
    req = {'text':'dictation', 'done':threading.Event(), 'cancelled':False, 'ok':False}
    bridge._begin(req)
    return bridge, clip, req


def test_restores_files_images_and_custom_mime(qt):
    bridge, clip, req = transaction(qt)
    bridge._restore(req)
    assert bytes(clip.mimeData().data('image/png')) == b'synthetic image bytes'
    assert bytes(clip.mimeData().data('text/uri-list')) == b'file:///tmp/example.txt\r\n'
    assert bytes(clip.mimeData().data('application/custom')) == b'custom data'


def test_new_copy_wins_even_when_same_text(qt):
    bridge, clip, req = transaction(qt)
    copied = QMimeData()
    copied.setText('dictation')
    clip.setMimeData(copied)
    bridge._restore(req)
    assert clip.mimeData() is copied


def test_cancelled_queued_request_does_not_change_clipboard(qt):
    bridge, clip, req = transaction(qt)
    bridge.close()
    original = clip.mimeData()
    req['cancelled'] = True
    bridge._begin(req)
    assert clip.mimeData() is original
    bridge.paste_keys.assert_not_called()


def test_copy_before_paste_prevents_wrong_paste(qt):
    bridge, clip, req = transaction(qt)
    copied = QMimeData()
    copied.setText('new copy')
    clip.setMimeData(copied)
    bridge._paste(req)
    bridge.paste_keys.assert_not_called()
    assert clip.mimeData() is copied


def test_native_qt_image_is_cloned(qt):
    original = QMimeData()
    image = QImage(2, 2, QImage.Format.Format_RGB32)
    image.fill(0xff00ff)
    original.setImageData(image)
    copied = clone_mime(original)
    assert copied.hasImage()
    assert copied.imageData().pixel(0, 0) == image.pixel(0, 0)


def test_worker_request_runs_on_gui_thread_and_completes(qt, monkeypatch):
    import time
    import clipboard_bridge
    monkeypatch.setattr(clipboard_bridge.db, 'get_setting', lambda key, default='': '100')
    source = QMimeData()
    source.setText('original')
    clipboard = FakeClipboard(source)
    seen = []
    bridge = ClipboardBridge(clipboard, lambda: seen.append((threading.get_ident(), clipboard.mimeData().text())))
    result = []
    worker = threading.Thread(target=lambda: result.append(bridge.inject('dictated')))
    worker.start()
    deadline = time.monotonic() + 3
    while worker.is_alive() and time.monotonic() < deadline:
        qt.processEvents()
        time.sleep(0.005)
    worker.join(timeout=0.1)
    assert not worker.is_alive()
    assert result == [True]
    assert seen == [(threading.get_ident(), 'dictated')]
    assert clipboard.mimeData().text() == 'original'
