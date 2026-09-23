import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEventLoop, QObject, QPoint, QPointF, QTimer, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication

from vigil_ui.app import create_engine, dispose_engine
from vigil_ui.i18n import TranslationBridge
from vigil_ui.overlay import OverlayModel
from vigil_ui.settings_model import SettingsModel
from vigil_ui.setup_model import SetupModel
from vigil_ui.theme import ThemeModel


def test_translation_bridge_switches_language_and_notifies():
    bridge = TranslationBridge("en")
    seen = []
    bridge.languageChanged.connect(lambda: seen.append(bridge.language))

    assert bridge.text("settings_title", bridge.revision) == "Settings"
    bridge.language = "fr"

    assert seen == ["fr"]
    assert bridge.text("settings_title", bridge.revision) == "Paramètres"


def test_fold_settings_qml_loads_offscreen():
    app = QApplication.instance() or QApplication([])
    engine, translator = create_engine(app, language="fr", visible=False)

    roots = engine.rootObjects()
    assert len(roots) == 1
    assert roots[0].objectName() == "settingsWindow"
    assert roots[0].width() == 600
    assert roots[0].height() == 640
    assert roots[0].title() == "Paramètres — Vigil"
    scroll = roots[0].findChild(QObject, "settingsScroll")
    assert scroll.property("contentHeight") > scroll.height()
    assert roots[0].property("previewMode") is True
    download = roots[0].findChild(QObject, "settingsDownloadProgress")
    assert download is not None
    fixture = engine._vigil_context_objects[1]
    fixture.begin_download()
    fixture.update_download(25, 100)
    app.processEvents()
    assert download.property("value") == 0.25
    fixture.finish_download()
    voice = roots[0].findChild(QObject, "voiceModelsGroup")
    general = roots[0].findChild(QObject, "generalGroup")
    assert voice.property("expanded") is True
    assert general.property("expanded") is False

    general.setProperty("expanded", True)
    translator.language = "en"
    app.processEvents()
    assert roots[0].title() == "Settings — Vigil"
    assert voice.property("expanded") is True
    assert general.property("expanded") is True

    # Keep context properties alive until the engine is torn down.
    assert translator.language == "en"
    dispose_engine(engine)


def test_theme_draft_preview_and_saved_palette_update_windows():
    app = QApplication.instance() or QApplication([])
    translator = TranslationBridge("en")
    settings = SettingsModel(translator)
    theme = ThemeModel()
    overlay = OverlayModel()
    engine, _ = create_engine(app, visible=False, translator=translator,
                              settings_model=settings, theme_model=theme,
                              overlay_model=overlay,
                              setup_model=SetupModel(translator, initial=True))
    window, overlay_window, setup = engine.rootObjects()
    preview = window.findChild(QObject, "themePreviewCard")
    panel = window.findChild(QObject, "themePreviewPanel")
    preview_glass = window.findChild(QObject, "themePreviewGlass")
    settings.setValue("theme_background", "#f8f0e0")
    settings.setValue("theme_surface", "#e8ddca")
    settings.setValue("theme_glass_opacity", "0.40")
    app.processEvents()
    assert preview.property("color").name() == "#f8f0e0"
    assert panel.property("color").name() == "#f8f0e0"
    assert preview_glass.property("color").name() == "#e8ddca"
    assert preview_glass.property("opacity") == 0.4
    assert window.property("color").name() == "#0a1019"
    theme.apply_values({"theme_background": "#f8f0e0", "theme_surface": "#e8ddca",
                        "theme_glass_opacity": "0.35"})
    app.processEvents()
    assert window.property("color").name() == "#f8f0e0"
    assert setup.property("color").name() == "#f8f0e0"
    glass = overlay_window.findChild(QObject, "answerCard")
    assert glass.property("color").alphaF() == pytest.approx(0.35, abs=0.01)
    overlay.close()
    dispose_engine(engine)


def test_settings_wheel_moves_by_90_pixels_and_touchpad_keeps_pixel_delta():
    app = QApplication.instance() or QApplication([])
    engine, _ = create_engine(app, visible=True)
    window = engine.rootObjects()[0]
    flick = window.findChild(QObject, "settingsScroll").property("contentItem")
    app.processEvents()

    def wheel(pixel, angle):
        event = QWheelEvent(QPointF(300, 300), QPointF(300, 300),
                            QPoint(0, pixel), QPoint(0, angle), Qt.NoButton,
                            Qt.NoModifier, Qt.ScrollUpdate, False)
        app.sendEvent(window, event)
        loop = QEventLoop()
        QTimer.singleShot(100, loop.quit)
        loop.exec()

    wheel(0, -120)
    assert flick.property("contentY") == 90
    wheel(-18, 0)
    assert flick.property("contentY") == 108
    dispose_engine(engine)


def test_complete_fold_qml_loads_and_overlay_does_not_take_focus():
    app = QApplication.instance() or QApplication([])
    translator = TranslationBridge("en")
    settings = SettingsModel(translator)
    overlay = OverlayModel()
    setup = SetupModel(translator, initial=True)
    engine, _ = create_engine(
        app, visible=False, translator=translator, settings_model=settings,
        overlay_model=overlay, setup_model=setup,
    )
    assert [root.objectName() for root in engine.rootObjects()] == [
        "settingsWindow", "overlayWindow", "setupWindow"
    ]
    setup_window = engine.rootObjects()[2]
    setup._busy = True
    setup._page = 6
    setup._set_download_progress("model", 50, 100)
    app.processEvents()
    progress = setup_window.findChild(QObject, "setupDownloadProgress")
    assert progress is not None
    assert progress.property("value") == 0.5
    assert progress.property("indeterminate") is False
    assert engine.rootObjects()[0].property("previewMode") is True
    assert engine.rootObjects()[0].findChild(QObject, "themeGroup") is not None
    overlay_window = engine.rootObjects()[1]
    assert QQuickWindow.hasDefaultAlphaBuffer()
    assert overlay_window.format().alphaBufferSize() > 0
    assert overlay_window.findChild(QObject, "answerCopyButton") is not None
    assert overlay_window.findChild(QObject, "answerCloseButton") is not None
    assert overlay_window.findChild(QObject, "answerEye") is not None
    assert overlay_window.findChild(QObject, "pillEye") is not None
    assert overlay_window.findChild(QObject, "answerCountdownFill") is not None
    assert overlay_window.findChild(QObject, "answerCountdownTrack").width() < 120
    assert overlay_window.property("contextEyeColor").name() == engine._vigil_context_objects[2].accentReadable
    overlay.set_context_state(2, False)
    app.processEvents()
    context_color = overlay_window.property("contextEyeColor")
    assert context_color.red() > context_color.green()
    overlay.set_context_state(2, True)
    app.processEvents()
    assert overlay_window.property("contextEyeColor").name() == "#ffd35a"
    overlay.set_context_state(0, False)
    assert not overlay_window.isVisible()
    overlay.show_message("Test", 1000)
    assert overlay_window.isVisible()
    assert not overlay_window.isActive()
    overlay.hide()
    dispose_engine(engine)


def test_answer_replaces_status_pill_until_followup_listening():
    app = QApplication.instance() or QApplication([])
    overlay = OverlayModel()
    engine, _ = create_engine(app, visible=False, overlay_model=overlay)
    window = engine.rootObjects()[1]
    pill = window.findChild(QObject, "statusPill")

    overlay.show_processing()
    app.processEvents()
    assert pill.isVisible()
    assert window.height() == 54

    overlay.show_answer("Answer")
    app.processEvents()
    assert not pill.isVisible()
    assert window.height() == 188

    overlay.set_context_state(1, True)
    overlay.show_assistant()
    app.processEvents()
    assert pill.isVisible()
    assert window.height() == 250

    overlay.close()
    dispose_engine(engine)


def test_streaming_answer_follows_tail_until_user_scrolls_up():
    app = QApplication.instance() or QApplication([])
    overlay = OverlayModel()
    engine, _ = create_engine(app, visible=False, overlay_model=overlay)
    window = engine.rootObjects()[1]
    scroll = window.findChild(QObject, "answerScroll")
    flick = scroll.property("contentItem")

    overlay.show_answer(" ".join(["A long answer arrives a few words at a time."] * 30))
    for _ in range(100):
        overlay._type_next()
    app.processEvents()
    app.processEvents()
    assert flick.property("contentHeight") > flick.height()
    assert flick.property("contentY") == flick.property("contentHeight") - flick.height()

    flick.setProperty("contentY", 20)
    app.processEvents()
    assert not scroll.property("followTail")
    for _ in range(20):
        overlay._type_next()
    app.processEvents()
    app.processEvents()
    assert flick.property("contentY") == 20

    flick.setProperty("contentY", flick.property("contentHeight") - flick.height())
    app.processEvents()
    assert scroll.property("followTail")
    for _ in range(30):
        overlay._type_next()
    app.processEvents()
    app.processEvents()
    assert flick.property("contentY") == flick.property("contentHeight") - flick.height()

    overlay.show_answer("A new answer")
    app.processEvents()
    app.processEvents()
    assert scroll.property("followTail")
    assert flick.property("contentY") == 0

    overlay.close()
    dispose_engine(engine)


def test_streaming_timer_keeps_autoscroll_and_manual_position():
    app = QApplication.instance() or QApplication([])
    overlay = OverlayModel()
    engine, _ = create_engine(app, visible=False, overlay_model=overlay)
    window = engine.rootObjects()[1]
    scroll = window.findChild(QObject, "answerScroll")
    flick = scroll.property("contentItem")

    overlay.show_answer(" ".join(["This sentence wraps as the answer streams in."] * 40))
    for _ in range(180):
        overlay._type_next()
    app.processEvents()

    def run_timer(milliseconds):
        loop = QEventLoop()
        QTimer.singleShot(milliseconds, loop.quit)
        loop.exec()

    run_timer(300)
    app.processEvents()
    app.processEvents()
    assert scroll.property("followTail")
    assert abs(flick.property("contentY") -
               (flick.property("contentHeight") - flick.height())) <= 1

    flick.setProperty("contentY", 20)
    app.processEvents()
    assert not scroll.property("followTail")
    height_before = flick.property("contentHeight")
    run_timer(650)
    assert flick.property("contentHeight") > height_before
    assert flick.property("contentY") == 20

    overlay.close()
    dispose_engine(engine)
