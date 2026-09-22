import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from locales import translate
from tray_qt import TrayIcon
from vigil_ui.i18n import TranslationBridge


def test_preview_tray_uses_selected_language_and_retranslates():
    app = QApplication.instance() or QApplication([])
    bridge = TranslationBridge("fr")
    tray = TrayIcon(
        on_quit=app.quit,
        on_show_settings=lambda: None,
        translate=lambda key: translate(key, language=bridge.language),
    )
    tray.start()
    bridge.languageChanged.connect(tray.retranslate)

    def labels():
        return [action.text() for action in tray._icon.contextMenu().actions()]

    assert "Paramètres" in labels()
    assert "Quitter" in labels()
    assert tray._icon.toolTip() == "Vigil — en attente"

    bridge.language = "en"
    assert "Settings" in labels()
    assert "Quit" in labels()
    assert tray._icon.toolTip() == "Vigil — idle"

    tray.set_recording(True)
    bridge.language = "fr"
    assert tray._icon.toolTip() == "Vigil — enregistrement..."
    tray.stop()
