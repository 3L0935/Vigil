import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication

from vigil_ui.app import create_engine, dispose_engine
from vigil_ui.i18n import TranslationBridge
from vigil_ui.overlay import OverlayModel
from vigil_ui.settings_model import SettingsModel
from vigil_ui.setup_model import SetupModel


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
