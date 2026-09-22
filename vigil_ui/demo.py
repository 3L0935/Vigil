"""Visual fixture entry point: ``python -m vigil_ui.demo``."""

import argparse
import sys

from PySide6.QtWidgets import QApplication

from locales import translate
from tray_qt import TrayIcon

from .app import create_engine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Open the Vigil Fold UI fixture")
    parser.add_argument("--language", choices=("en", "fr", "it"), default="en")
    args = parser.parse_args(argv)

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Vigil")
    engine, translator = create_engine(app, language=args.language)
    if not engine.rootObjects():
        return 1
    window = engine.rootObjects()[0]
    app.setQuitOnLastWindowClosed(False)

    def show_settings():
        window.show()
        window.raise_()
        window.requestActivate()

    tray = TrayIcon(
        on_quit=app.quit,
        on_show_settings=show_settings,
        translate=lambda key: translate(key, language=translator.language),
    )
    tray.start()
    translator.languageChanged.connect(tray.retranslate)
    app.aboutToQuit.connect(tray.stop)
    # Explicit references document and preserve context object lifetimes.
    app._vigil_engine = engine
    app._vigil_i18n = translator
    app._vigil_tray = tray
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
