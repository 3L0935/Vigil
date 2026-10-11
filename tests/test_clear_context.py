"""Clearing the context must answer to the words the app itself puts forward.

The tray menu offers "Effacer le contexte". That exact request used to do
nothing, because the matcher compared the whole transcript against a fixed
list that only knew "efface la conversation".
"""

import pytest

from assistant import _is_clear_context_request, _normalise_request


# ── The wording the interface suggests ────────────────────────────────────

@pytest.mark.parametrize("text", [
    "Effacer le contexte",
    "efface le contexte",
    "efface le contexte.",
    "Efface le contexte s'il te plaît",
    "ok, efface le contexte",
    "bon, efface le contexte",
])
def test_the_tray_menu_wording_clears_the_context(text):
    assert _is_clear_context_request(text)


# ── Everything that already worked must keep working ─────────────────────

@pytest.mark.parametrize("text", [
    "nettoie la conv", "nettoie la conversation",
    "efface la conv", "efface la conversation",
    "repart à zéro", "repart a zero",
    "recommence", "remet à zéro", "remet a zero",
    "clear context", "reset context", "start over", "start fresh",
    "pulisci la conversazione", "ricomincia", "azzera",
])
def test_the_previous_phrasings_still_clear_the_context(text):
    assert _is_clear_context_request(text)


# ── Dictation drops accents, so the matcher must not care ────────────────

@pytest.mark.parametrize("text", [
    "efface le contexte",       # accents absent
    "réinitialise la conversation",
    "reinitialise la conversation",
    "vide l'historique",
    "oublie tout",
    "remets tout à zéro",
])
def test_accent_and_elision_variants(text):
    assert _is_clear_context_request(text)


def test_english_and_italian_phrasings():
    for text in ("clear the conversation", "reset my chat", "wipe the context",
                 "cancella la conversazione", "azzera la memoria"):
        assert _is_clear_context_request(text), text


# ── Nothing else may clear the conversation ──────────────────────────────

@pytest.mark.parametrize("text", [
    "",
    "   ",
    "n'efface pas la conversation",
    "ne nettoie pas la conversation",
    "efface ce fichier",
    "nettoie le bureau",
    "ouvre Chrome",
    "quelle heure est-il",
    "fais un résumé de la conversation",
    "recommence la chanson",
])
def test_unrelated_requests_are_left_alone(text):
    assert not _is_clear_context_request(text)


def test_normalisation_strips_accents_case_and_spacing():
    assert _normalise_request("  Effacer  le CONTEXTE ! ") == "effacer le contexte"
    assert _normalise_request("Réinitialise") == "reinitialise"
    assert _normalise_request("déjà") == "deja"


def test_an_empty_request_never_clears():
    assert not _is_clear_context_request("")
    assert not _is_clear_context_request("?!...")
