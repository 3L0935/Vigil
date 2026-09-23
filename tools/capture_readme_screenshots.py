"""Capture reproducible English README images from the current Qt UI."""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QObject, QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from vigil_ui.app import create_engine, dispose_engine  # noqa: E402
from vigil_ui.i18n import TranslationBridge  # noqa: E402
from vigil_ui.overlay import OverlayModel  # noqa: E402
from vigil_ui.settings_model import SettingsModel  # noqa: E402
from vigil_ui.setup_model import SetupModel  # noqa: E402


OUTPUT = ROOT / "img" / "screenshots"


def settle(milliseconds=220):
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def capture(window, name):
    image = window.grabWindow()
    if image.isNull() or not image.save(str(OUTPUT / name)):
        raise RuntimeError(f"Could not capture {name}")
    print(f"{name}: {image.width()} x {image.height()}")


def main():
    app = QApplication.instance() or QApplication([])
    translator = TranslationBridge("en")
    settings = SettingsModel(translator, preview=False)
    setup = SetupModel(translator, initial=True)
    overlay = OverlayModel()
    engine, _ = create_engine(
        app, language="en", visible=True, translator=translator,
        settings_model=settings, setup_model=setup, overlay_model=overlay,
    )
    settings_window, overlay_window, setup_window = engine.rootObjects()

    try:
        settle()
        capture(settings_window, "settings-en.png")

        setup._page = 1
        setup.setValue("llama_backend", "vulkan")
        settle()
        capture(setup_window, "setup-en.png")

        settings_window.findChild(QObject, "voiceModelsGroup").setProperty("expanded", False)
        theme_group = settings_window.findChild(QObject, "themeGroup")
        theme_group.setProperty("expanded", True)
        settle(300)
        scroll = settings_window.findChild(QObject, "settingsScroll").property("contentItem")
        scroll.setProperty("contentY", max(0, theme_group.y() - 15))
        settle(80)
        capture(settings_window, "settings-theme-en.png")
        scroll.setProperty("contentY", theme_group.y() + theme_group.height()
                           - scroll.height() + 8)
        settle(80)
        capture(settings_window, "settings-theme-opacity-en.png")

        overlay.show_recording()
        overlay.update_level(0.62)
        settle()
        capture(overlay_window, "pill-recording-en.png")
        overlay.show_assistant()
        overlay.update_level(0.78)
        settle()
        capture(overlay_window, "pill-assistant-en.png")
        overlay.show_processing()
        settle()
        capture(overlay_window, "pill-processing-en.png")

        overlay.show_answer(
            "Vigil can dictate into any app, search your notes, and answer "
            "questions while your data stays on your device."
        )
        overlay._type_timer.stop()
        overlay._visible_answer = overlay._answer
        overlay._deadline_ms = 6400
        overlay._answer_timer.stop()
        overlay.changed.emit()
        settle()
        capture(overlay_window, "answer-en.png")
    finally:
        overlay.close()
        dispose_engine(engine)


if __name__ == "__main__":
    main()
