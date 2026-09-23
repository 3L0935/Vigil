"""Shared, validated palette for all Qt Quick windows."""

import re

from PySide6.QtCore import QObject, Property, Signal
from PySide6.QtGui import QColor


DEFAULTS = {
    "theme_accent_a": "#6aafbe",
    "theme_accent_b": "#a78bfa",
    "theme_gradient": "true",
    "theme_reduced_motion": "false",
}

_HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}\Z")


def validated_theme(values):
    """Return canonical values or reject an invalid settings draft."""
    result = {}
    for key in ("theme_accent_a", "theme_accent_b"):
        value = str(values.get(key, DEFAULTS[key])).strip()
        if not _HEX_COLOR.fullmatch(value) or not QColor(value).isValid():
            raise ValueError(f"Invalid theme color: {key}")
        result[key] = value.lower()
    for key in ("theme_gradient", "theme_reduced_motion"):
        value = str(values.get(key, DEFAULTS[key])).lower()
        if value not in ("true", "false"):
            raise ValueError(f"Invalid theme option: {key}")
        result[key] = value
    return result


class ThemeModel(QObject):
    changed = Signal()

    def __init__(self, values=None, parent=None):
        super().__init__(parent)
        try:
            self._values = validated_theme(values or DEFAULTS)
        except ValueError:
            self._values = dict(DEFAULTS)

    def apply_values(self, values):
        updated = validated_theme(values)
        if updated != self._values:
            self._values = updated
            self.changed.emit()

    @Property(str, notify=changed)
    def accentA(self):
        return self._values["theme_accent_a"]

    @Property(str, notify=changed)
    def accentB(self):
        return self._values["theme_accent_b"]

    @Property(bool, notify=changed)
    def gradientEnabled(self):
        return self._values["theme_gradient"] == "true"

    @Property(bool, notify=changed)
    def reducedMotion(self):
        return self._values["theme_reduced_motion"] == "true"

    @Property(str, constant=True)
    def background(self):
        return "#0a1019"

    @Property(str, constant=True)
    def surface(self):
        return "#151e2b"

    @Property(str, constant=True)
    def raised(self):
        return "#1c2939"

    @Property(str, constant=True)
    def control(self):
        return "#111b29"

    @Property(str, constant=True)
    def glass(self):
        return "#b8142030"

    @Property(str, constant=True)
    def panelGlass(self):
        return "#eb151f2e"

    @Property(str, constant=True)
    def text(self):
        return "#edf4fb"

    @Property(str, constant=True)
    def muted(self):
        return "#a1b2c4"

    @Property(str, constant=True)
    def faint(self):
        return "#7f90a5"

    @Property(str, constant=True)
    def line(self):
        return "#34485b"

    @Property(str, notify=changed)
    def accentReadable(self):
        """Brighten user color until it reads on dark surfaces."""
        color = QColor(self.accentA)
        if color.lightness() < 175:
            color.setHsl(max(0, color.hslHue()), color.hslSaturation(), 175)
        return color.name()
