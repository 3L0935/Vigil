"""Shared theme values remain valid and readable."""

import pytest

from vigil_ui.theme import ThemeModel, validated_theme


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
