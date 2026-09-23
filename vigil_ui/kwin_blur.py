"""Request KWin's blur behind effect for the visible XWayland overlay surfaces."""

import os
import shutil
import subprocess

from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication


_ATOM = "_KDE_NET_WM_BLUR_BEHIND_REGION"


def _rounded_rectangles(item, scale):
    """Approximate a rounded QML rectangle without blurring transparent corners."""
    x = round(item.x() * scale)
    y = round(item.y() * scale)
    width = round(item.width() * scale)
    height = round(item.height() * scale)
    radius = min(round(item.property("radius") * scale), width // 2, height // 2)
    bands = (
        (radius, 0),
        (round(radius * 0.5), round(radius * 0.12)),
        (round(radius * 0.2), round(radius * 0.32)),
        (0, round(radius * 0.8)),
    )
    return [
        (x + inset, y + top, width - 2 * inset, height - 2 * top)
        for inset, top in bands if width > 2 * inset and height > 2 * top
    ]


def request_kwin_blur(window):
    """Return None if unsupported, False if not ready, True when requested."""
    if (QGuiApplication.platformName() != "xcb"
            or "kde" not in os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
            or not shutil.which("xprop")):
        return None

    scale = window.devicePixelRatio()
    rectangles = []
    for name in ("answerCard", "statusPill"):
        if name == "statusPill" and not window.property("pillVisible"):
            continue
        item = window.findChild(QObject, name)
        if item is None:
            return False
        if name == "answerCard" and window.height() > 100 and not item.isVisible():
            return False
        if name == "statusPill" and not item.isVisible():
            return False
        if item.isVisible():
            if item.x() < 0 or item.y() < 0 or item.width() <= 0 or item.height() <= 0:
                return False
            rectangles.extend(_rounded_rectangles(item, scale))
    if not rectangles:
        return False

    region = ",".join(str(value) for rect in rectangles for value in rect)
    try:
        result = subprocess.run(
            ["xprop", "-id", hex(window.winId()), "-f", _ATOM, "32c",
             "-set", _ATOM, region],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False, timeout=1,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0
