"""Visual fixture entry point: ``python -m vigil_ui.demo``."""

import argparse
import sys

from PySide6.QtWidgets import QApplication

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
    # Explicit references document and preserve context object lifetimes.
    app._vigil_engine = engine
    app._vigil_i18n = translator
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
