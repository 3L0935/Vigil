# tests/test_locales.py
import string
from pathlib import Path
import re
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_all_languages_have_the_same_keys():
    from locales import _STRINGS
    expected = set(_STRINGS["en"])
    for lang, translations in _STRINGS.items():
        assert set(translations) == expected, f"Key mismatch in '{lang}'"


def test_all_languages_keep_the_same_format_placeholders():
    from locales import _STRINGS
    formatter = string.Formatter()

    def fields(value):
        return {name for _, name, _, _ in formatter.parse(value) if name}

    for key, english in _STRINGS["en"].items():
        for lang in ("fr", "it"):
            assert fields(_STRINGS[lang][key]) == fields(english), (lang, key)


def test_translate_can_select_language_without_mutating_config():
    import config
    from locales import translate

    previous = config.LANGUAGE
    assert translate("setting_language", language="en") == "Language"
    assert translate("setting_language", language="fr") == "Langue"
    assert config.LANGUAGE == previous


def test_qml_translation_keys_exist_in_every_language():
    from locales import _STRINGS

    qml_dir = Path(__file__).resolve().parents[1] / "vigil_ui" / "qml"
    used = set()
    for path in qml_dir.rglob("*.qml"):
        used.update(re.findall(r'i18n\.text(?:WithValue)?\("([^"]+)"', path.read_text()))
    assert used
    for language, translations in _STRINGS.items():
        assert used <= translations.keys(), (language, sorted(used - translations.keys()))
