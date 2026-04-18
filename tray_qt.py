"""Qt-based system tray icon — works natively on KDE Wayland/X11."""

import sys
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QImage
from PIL import Image

import locales


def _pil_to_qicon(img: Image.Image) -> QIcon:
    img = img.convert("RGBA")
    w, h = img.size
    data = img.tobytes("raw", "RGBA")
    qimg = QImage(data, w, h, QImage.Format.Format_RGBA8888)
    return QIcon(QPixmap.fromImage(qimg))


class TrayIcon:
    def __init__(self, on_quit, on_show_settings=None,
                 on_dictate=None, on_assist=None, on_stop_tts=None,
                 on_clear_context=None):
        self._on_quit = on_quit
        self._on_show_settings = on_show_settings
        self._on_dictate = on_dictate
        self._on_assist = on_assist
        self._on_stop_tts = on_stop_tts
        self._on_clear_context = on_clear_context
        self._dict_label = "Dictate"
        self._asst_label = "Assistant"
        self._app = None
        self._icon = None

    def start(self):
        from brand import make_tray_icon
        if not QApplication.instance():
            self._app = QApplication(sys.argv)

        img = make_tray_icon(recording=False)
        self._icon = QSystemTrayIcon(_pil_to_qicon(img))
        self._icon.setToolTip(locales.get("tray_idle"))
        self._icon.setContextMenu(self._build_menu())
        self._icon.show()

    def _build_menu(self) -> QMenu:
        menu = QMenu()
        menu.addAction("Vigil").setEnabled(False)
        menu.addSeparator()
        if self._on_dictate:
            menu.addAction(self._dict_label, self._on_dictate)
        if self._on_assist:
            menu.addAction(self._asst_label, self._on_assist)
        if self._on_stop_tts:
            menu.addAction(locales.get("tray_stop_tts"), self._on_stop_tts)
        if self._on_clear_context:
            menu.addAction(locales.get("tray_clear_context"), self._on_clear_context)
        if self._on_dictate or self._on_assist or self._on_stop_tts or self._on_clear_context:
            menu.addSeparator()
        if self._on_show_settings:
            menu.addAction(locales.get("tray_settings"), self._on_show_settings)
        if self._on_show_settings:
            menu.addSeparator()
        menu.addAction(locales.get("tray_quit"), self._on_quit)
        return menu

    def update_hotkey_labels(self, dict_label: str, asst_label: str):
        self._dict_label = dict_label
        self._asst_label = asst_label
        if self._icon:
            self._icon.setContextMenu(self._build_menu())

    def process_events(self):
        if self._app:
            self._app.processEvents()

    def set_recording(self, recording: bool):
        if self._icon is None:
            return
        from brand import make_tray_icon
        img = make_tray_icon(recording=recording)
        self._icon.setIcon(_pil_to_qicon(img))
        self._icon.setToolTip(
            locales.get("tray_recording") if recording else locales.get("tray_idle")
        )

    def set_tooltip(self, text: str):
        if self._icon:
            self._icon.setToolTip(text)

    def stop(self):
        if self._icon:
            self._icon.hide()
            self._icon = None
