"""Shared theme values remain valid and readable."""

import pytest

from vigil_ui.settings_schema import FIELDS
from vigil_ui.theme import DEFAULTS, PRESETS, ThemeModel, matching_preset, validated_theme


def test_theme_normalizes_hex_and_rejects_invalid_values():
    values = validated_theme({"theme_accent_a": "#AABBCC"})
    assert values["theme_accent_a"] == "#aabbcc"
    with pytest.raises(ValueError):
        validated_theme({"theme_accent_a": "black"})
    with pytest.raises(ValueError):
        validated_theme({"theme_gradient": "maybe"})


def test_dark_accent_keeps_readable_text_and_bad_saved_theme_falls_back():
    theme = ThemeModel({"theme_accent_a": "#000000"})
    assert theme.accentReadable != "#000000"
    assert ThemeModel({"theme_accent_a": "bad"}).accentA == "#6aafbe"


def test_every_editable_theme_field_is_validated_and_updates_derived_surfaces():
    fields = {field.key for field in FIELDS if field.group == "theme"}
    assert fields == set(DEFAULTS)
    theme = ThemeModel()
    changes = []
    theme.changed.connect(lambda: changes.append(theme.background))
    theme.apply_values({
        "theme_background": "#F8F0E0",
        "theme_surface": "#e8ddca",
        "theme_raised": "#d9cab4",
        "theme_control": "#fffaf0",
        "theme_text": "#332211",
        "theme_muted": "#665544",
        "theme_line": "#998877",
        "theme_accent_a": "#224488",
        "theme_glass_opacity": "0.35",
        "theme_window_opacity": "0.50",
    })
    assert changes == ["#f8f0e0"]
    assert theme.surface == "#e8ddca"
    assert theme.raised == "#d9cab4"
    assert theme.control == "#fffaf0"
    assert theme.text == "#332211"
    assert theme.muted == "#665544"
    assert theme.line == "#998877"
    assert theme.glass.startswith("#59")
    assert theme.windowBackground.startswith("#80")
    assert theme.panelGlass.startswith("#77")
    assert theme.backgroundTop != DEFAULTS["theme_background"]


def test_invalid_glass_opacity_and_light_surface_accent():
    for value in ("0.1", "1.1", "nan", "abc"):
        with pytest.raises(ValueError):
            validated_theme({"theme_glass_opacity": value})
    for value in ("0.2", "1.1", "nan", "abc"):
        with pytest.raises(ValueError):
            validated_theme({"theme_window_opacity": value})
    theme = ThemeModel({"theme_surface": "#ffffff", "theme_accent_a": "#eeeeee"})
    assert theme.accentReadable != "#eeeeee"


def test_classic_presets_are_complete_and_custom_edits_clear_selection():
    assert set(PRESETS) == {"vigil", "classic_dark", "classic_light", "high_contrast"}
    assert matching_preset(DEFAULTS) == "vigil"
    for name, colors in PRESETS.items():
        assert matching_preset(colors) == name
        assert validated_theme(colors)
    assert matching_preset({**PRESETS["classic_light"], "theme_accent_a": "#ff0000"}) == "custom"
    assert matching_preset({**PRESETS["classic_light"], "theme_window_opacity": "0.5"}) == "classic_light"
