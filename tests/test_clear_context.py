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


# ── Wrapping the request in politeness must not hide it ───────────────────
# Observed: "clear la conversation stp" reached the model, which had no way to
# do it and answered that it could not. The shortcut only knew the bare verb.

@pytest.mark.parametrize("text", [
    "clear la conversation stp",
    "Vigil, tu peux effacer la conversation ?",
    "peux-tu clear la conversation",
    "est-ce que tu peux effacer la conversation",
    "s'il te plaît efface la conversation",
    "j'aimerais que tu effaces la conversation",
    "il faut que tu vides la conversation",
    "xana, efface le contexte",
    "supprime le contexte",
    "supprime l'historique",
    "oublie cette conversation",
    "supprime ces conversations",
])
def test_a_wrapped_request_still_clears_the_context(text):
    assert _is_clear_context_request(text)


def test_normalisation_folds_apostrophes_and_hyphens():
    assert _normalise_request("Peux-tu clear l'historique ?") == "peux tu clear l historique"


# ── The tool left to the model, as a net under the shortcut ───────────────

def test_the_tool_is_offered_to_the_model():
    from assistant import _get_tools
    names = [tool["function"]["name"] for tool in _get_tools()]
    assert "clear_context" in names


def test_the_tool_clears_the_context_and_answers_with_the_shared_wording():
    import assistant
    assistant._conversation_history = [{"role": "user", "content": "bonjour"}]
    result = assistant._dispatch("clear_context", {})
    assert assistant._conversation_history == []
    assert assistant._render_tool_result(result) == assistant.locales.get("context_cleared")
