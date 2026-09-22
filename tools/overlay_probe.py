"""Measure Qt Quick overlay behavior on the current desktop.

Run separately with ``QT_QPA_PLATFORM=wayland`` and ``QT_QPA_PLATFORM=xcb``.
The script opens a small overlay at each requested anchor, then prints JSON
observations. It changes no compositor or desktop settings.
"""

import argparse
import json
import sys

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication


ANCHORS = (
    "top-left", "top-center", "top-right",
    "center-left", "center", "center-right",
    "bottom-left", "bottom-center", "bottom-right",
)


def anchor_position(rect, width: int, height: int, anchor: str, margin: int = 24):
    vertical, _, horizontal = anchor.partition("-")
    if anchor == "center":
        vertical, horizontal = "center", "center"
    if horizontal == "":
        horizontal = "center"
    x = {
        "left": rect.x() + margin,
        "center": rect.x() + (rect.width() - width) // 2,
        "right": rect.x() + rect.width() - width - margin,
    }[horizontal]
    y = {
        "top": rect.y() + margin,
        "center": rect.y() + (rect.height() - height) // 2,
        "bottom": rect.y() + rect.height() - height - margin,
    }[vertical]
    return x, y


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delay-ms", type=int, default=220)
    args = parser.parse_args(argv)

    app = QApplication.instance() or QApplication(sys.argv)
    screens = app.screens()
    if not screens:
        print(json.dumps({"error": "No Qt screens available"}))
        return 2

    # Qt can recreate QScreen wrappers while native windows move between
    # outputs. Keep names, and resolve the current object for each case.
    cases = [(screen.name(), anchor) for screen in screens for anchor in ANCHORS]
    state = {"index": 0, "window": None}
    platform = app.platformName()

    def next_case():
        if state["window"] is not None:
            state["window"].close()
            state["window"].deleteLater()
        if state["index"] >= len(cases):
            app.quit()
            return

        screen_name, anchor = cases[state["index"]]
        state["index"] += 1
        screen = next((item for item in app.screens() if item.name() == screen_name), None)
        if screen is None:
            print(json.dumps({
                "platform": platform,
                "screen": screen_name,
                "anchor": anchor,
                "error": "Screen disappeared during probe",
            }), flush=True)
            QTimer.singleShot(0, next_case)
            return
        requested = anchor_position(screen.availableGeometry(), 252, 50, anchor)
        scale = screen.devicePixelRatio()
        window = QQuickWindow()
        window.setScreen(screen)
        window.setColor(QColor("#0e131d"))
        window.setFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        window.resize(252, 50)
        window.setPosition(*requested)
        window.show()
        state["window"] = window

        def observe():
            actual = window.position()
            actual_screen = window.screen()
            flags = window.flags()
            print(json.dumps({
                "platform": platform,
                "screen": screen_name,
                "actual_screen": actual_screen.name() if actual_screen else None,
                "scale": scale,
                "anchor": anchor,
                "requested": requested,
                "observed": [actual.x(), actual.y()],
                "visible": window.isVisible(),
                "active": window.isActive(),
                "always_on_top_hint": bool(flags & Qt.WindowType.WindowStaysOnTopHint),
                "no_focus_hint": bool(flags & Qt.WindowType.WindowDoesNotAcceptFocus),
            }), flush=True)
            QTimer.singleShot(0, next_case)

        QTimer.singleShot(args.delay_ms, observe)

    QTimer.singleShot(0, next_case)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
