"""Shared, validated palette for all Qt Quick windows."""

import re

from PySide6.QtCore import QObject, Property, Signal
from PySide6.QtGui import QColor


DEFAULTS = {
    "theme_background": "#0a1019",
    "theme_surface": "#151e2b",
    "theme_raised": "#1c2939",
    "theme_control": "#111b29",
    "theme_text": "#edf4fb",
    "theme_muted": "#a1b2c4",
    "theme_line": "#34485b",
    "theme_accent_a": "#6aafbe",
    "theme_accent_b": "#a78bfa",
    "theme_glass_opacity": "0.53",
    "theme_gradient": "true",
    "theme_reduced_motion": "false",
}

_HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}\Z")
_COLOR_KEYS = tuple(key for key in DEFAULTS if key not in (
    "theme_glass_opacity", "theme_gradient", "theme_reduced_motion"
))


def _alpha(color, opacity):
    value = QColor(color)
    value.setAlphaF(opacity)
    return value.name(QColor.HexArgb)


def _mix(first, second, amount):
    a, b = QColor(first), QColor(second)
    return QColor.fromRgbF(
        a.redF() * (1 - amount) + b.redF() * amount,
        a.greenF() * (1 - amount) + b.greenF() * amount,
        a.blueF() * (1 - amount) + b.blueF() * amount,
    ).name()


def _luminance(color):
    channels = (QColor(color).redF(), QColor(color).greenF(), QColor(color).blueF())
    linear = tuple(channel / 12.92 if channel <= 0.04045
                   else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels)
    return sum(weight * channel for weight, channel in zip((0.2126, 0.7152, 0.0722), linear))


def _contrast(first, second):
    light, dark = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def validated_theme(values):
    """Return canonical values or reject an invalid settings draft."""
    result = {}
    for key in _COLOR_KEYS:
        value = str(values.get(key, DEFAULTS[key])).strip()
        if not _HEX_COLOR.fullmatch(value) or not QColor(value).isValid():
            raise ValueError(f"Invalid theme color: {key}")
        result[key] = value.lower()
    for key in ("theme_gradient", "theme_reduced_motion"):
        value = str(values.get(key, DEFAULTS[key])).lower()
        if value not in ("true", "false"):
            raise ValueError(f"Invalid theme option: {key}")
        result[key] = value
    try:
        opacity = float(values.get("theme_glass_opacity", DEFAULTS["theme_glass_opacity"]))
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid theme glass opacity") from exc
    if not 0.25 <= opacity <= 1:
        raise ValueError("Invalid theme glass opacity")
    result["theme_glass_opacity"] = f"{opacity:.2f}"
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

    @Property(str, notify=changed)
    def background(self):
        return self._values["theme_background"]

    @Property(str, notify=changed)
    def backgroundTop(self):
        return _mix(self.background, self.raised, 0.45)

    @Property(str, notify=changed)
    def surface(self):
        return self._values["theme_surface"]

    @Property(str, notify=changed)
    def raised(self):
        return self._values["theme_raised"]

    @Property(str, notify=changed)
    def control(self):
        return self._values["theme_control"]

    @Property(float, notify=changed)
    def glassOpacity(self):
        return float(self._values["theme_glass_opacity"])

    @Property(str, notify=changed)
    def glass(self):
        return _alpha(self.surface, self.glassOpacity)

    @Property(str, notify=changed)
    def glassTop(self):
        return _alpha(self.raised, min(1, self.glassOpacity + 0.10))

    @Property(str, notify=changed)
    def panelGlass(self):
        return _alpha(self.surface, min(1, self.glassOpacity + 0.40))

    @Property(str, notify=changed)
    def foldTop(self):
        return _alpha(self.raised, min(1, self.glassOpacity + 0.40))

    @Property(str, notify=changed)
    def text(self):
        return self._values["theme_text"]

    @Property(str, notify=changed)
    def muted(self):
        return self._values["theme_muted"]

    @Property(str, notify=changed)
    def faint(self):
        return QColor(self.muted).darker(125).name()

    @Property(str, notify=changed)
    def line(self):
        return self._values["theme_line"]

    @Property(str, notify=changed)
    def accentReadable(self):
        """Keep the chosen hue legible on both dark and light surfaces."""
        color = QColor(self.accentA)
        direction = 1 if _luminance(self.surface) < 0.5 else -1
        while _contrast(color, self.surface) < 4.5:
            lightness = max(0, min(255, color.lightness() + direction * 5))
            if lightness == color.lightness():
                break
            color.setHsl(max(0, color.hslHue()), color.hslSaturation(), lightness)
        return color.name()
