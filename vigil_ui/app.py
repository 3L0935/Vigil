"""Creation helpers for the standalone Qt Quick UI."""

from pathlib import Path
import sys
import shiboken6

from PySide6.QtCore import QUrl
from PySide6.QtGui import QFont
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication
from PySide6.QtQuickControls2 import QQuickStyle

from .i18n import TranslationBridge
from .settings_model import SettingsModel

_QML_DIR = Path(__file__).with_name("qml")


def create_engine(
    app: QApplication,
    *,
    language: str = "en",
    visible: bool = True,
    translator: TranslationBridge | None = None,
    settings_model: SettingsModel | None = None,
    overlay_model=None,
    setup_model=None,
) -> tuple[QQmlApplicationEngine, TranslationBridge]:
    """Load the Fold settings fixture and retain its context objects."""
    if sys.platform.startswith("linux"):
        app.setFont(QFont("DejaVu Sans"))
    elif sys.platform == "win32":
        app.setFont(QFont("Segoe UI"))
    QQuickStyle.setStyle("Fusion")
    engine = QQmlApplicationEngine(app)
    translator = translator or TranslationBridge(language)
    settings_model = settings_model or SettingsModel(translator)
    # Python owns these context objects until all QML roots are destroyed.
    # Parenting them to the engine destroys them before binding teardown.
    engine._vigil_context_objects = (translator, settings_model, overlay_model, setup_model)
    context = engine.rootContext()
    context.setContextProperty("i18n", translator)
    context.setContextProperty("settingsModel", settings_model)
    if overlay_model is not None:
        context.setContextProperty("overlayModel", overlay_model)
    if setup_model is not None:
        context.setContextProperty("setupModel", setup_model)
        context.setContextProperty("setupVisible", bool(setup_model.initial))
    context.setContextProperty("startVisible", visible)
    engine.addImportPath(str(_QML_DIR))
    engine.load(QUrl.fromLocalFile(str(_QML_DIR / "SettingsWindow.qml")))
    if overlay_model is not None:
        engine.load(QUrl.fromLocalFile(str(_QML_DIR / "OverlayWindow.qml")))
        if len(engine.rootObjects()) > 1:
            overlay_model.attach_window(engine.rootObjects()[1])
    if setup_model is not None:
        engine.load(QUrl.fromLocalFile(str(_QML_DIR / "SetupWindow.qml")))
    return engine, translator


def dispose_engine(engine: QQmlApplicationEngine) -> None:
    """Destroy QML windows before context objects to avoid teardown callbacks."""
    for root in reversed(engine.rootObjects()):
        shiboken6.delete(root)
    shiboken6.delete(engine)
