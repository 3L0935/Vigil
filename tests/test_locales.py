# tests/test_locales.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_all_en_keys_present_in_fr_and_it():
    """Every key in the English table must exist in French and Italian."""
    from locales import _STRINGS
    en_keys = set(_STRINGS["en"].keys())
    for lang in ("fr", "it"):
        missing = en_keys - set(_STRINGS[lang].keys())
        assert not missing, f"Keys missing in '{lang}': {sorted(missing)}"
