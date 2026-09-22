"""Creation helpers for the standalone Qt Quick UI."""

from pathlib import Path
import sys

from PySide6.QtCore import QUrl
from PySide6.QtGui import QFont
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication
from PySide6.QtQuickControls2 import QQuickStyle

from .i18n import TranslationBridge

_QML_DIR = Path(__file__).with_name("qml")


def create_engine(
    app: QApplication,
    *,
    language: str = "en",
    visible: bool = True,
) -> tuple[QQmlApplicationEngine, TranslationBridge]:
    """Load the Fold settings fixture and retain its context objects."""
    if sys.platform.startswith("linux"):
        app.setFont(QFont("DejaVu Sans"))
    elif sys.platform == "win32":
        app.setFont(QFont("Segoe UI"))
    QQuickStyle.setStyle("Fusion")
    engine = QQmlApplicationEngine(app)
    translator = TranslationBridge(language, parent=engine)
    context = engine.rootContext()
    context.setContextProperty("i18n", translator)
    context.setContextProperty("startVisible", visible)
    engine.addImportPath(str(_QML_DIR))
    engine.load(QUrl.fromLocalFile(str(_QML_DIR / "SettingsWindow.qml")))
    return engine, translator
