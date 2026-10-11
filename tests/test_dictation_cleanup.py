"""The dictation cleanup pass must never cost a dictation."""

from unittest.mock import Mock

import pytest

import dictation_cleanup
import privacy


@pytest.fixture
def backend(monkeypatch):
    """Replace the LLM stack; return a setter for the raw response dict."""
    state = {"response": None, "error": None, "calls": []}

    def chat(messages, tools=None, **kwargs):
        state["calls"].append({"messages": messages, **kwargs})
        if state["error"]:
            raise state["error"]
        return state["response"]

    monkeypatch.setattr(dictation_cleanup, "_backend",
                        lambda: (Mock(chat=chat), ""))
    import llm_manager
    monkeypatch.setattr(llm_manager.manager, "ensure_running", Mock())
    return state


def reply(content, finish_reason="stop"):
    return {"choices": [{"finish_reason": finish_reason, "message": {"content": content}}]}


def test_cleanup_returns_the_model_text(backend):
    backend["response"] = reply("Bonjour, je teste le nettoyage.")
    assert dictation_cleanup.cleanup("euh bonjour euh je teste le nettoyage") == \
        "Bonjour, je teste le nettoyage."


def test_cleanup_asks_for_local_data_only(backend):
    backend["response"] = reply("ok")
    dictation_cleanup.cleanup("euh ok")
    call = backend["calls"][0]
    assert call["local_data"] is True
    assert call["max_tokens"] == dictation_cleanup._MAX_TOKENS


def test_system_prompt_is_sent_with_the_transcript(backend):
    backend["response"] = reply("ok")
    dictation_cleanup.cleanup("euh ok")
    messages = backend["calls"][0]["messages"]
    assert messages[0]["role"] == "system"
    assert "filler" in messages[0]["content"]
    assert messages[1] == {"role": "user", "content": "euh ok"}


def test_no_model_response_keeps_the_raw_text(backend):
    backend["response"] = None
    assert dictation_cleanup.cleanup("euh bonjour") == "euh bonjour"


def test_empty_model_output_keeps_the_raw_text(backend):
    backend["response"] = reply("   ")
    assert dictation_cleanup.cleanup("euh bonjour") == "euh bonjour"


def test_truncated_output_is_refused(backend):
    backend["response"] = reply("Bonjour je", finish_reason="length")
    assert dictation_cleanup.cleanup("euh bonjour je teste") == "euh bonjour je teste"


def test_an_answer_instead_of_a_rewrite_is_refused(backend):
    backend["response"] = reply(
        "Voici le texte nettoye : Bonjour. J'ai aussi remplace les repetitions et "
        "corrige la ponctuation, ce qui donne une phrase bien plus longue que "
        "l'entree d'origine et ne doit jamais etre collee dans le document.")
    raw = "euh bonjour"
    assert dictation_cleanup.cleanup(raw) == raw


def test_an_over_aggressive_summary_is_refused(backend):
    backend["response"] = reply("Bonjour")
    raw = "euh bonjour je voulais te dire que la reunion de demain est annulee " \
          "et qu on peut se voir plutot vendredi matin si ca te va"
    assert dictation_cleanup.cleanup(raw) == raw


def test_wrapping_quotes_are_removed(backend):
    backend["response"] = reply('"Bonjour le monde."')
    assert dictation_cleanup.cleanup("euh bonjour le monde") == "Bonjour le monde."


def test_code_fence_is_removed(backend):
    backend["response"] = reply("```\nBonjour le monde.\n```")
    assert dictation_cleanup.cleanup("euh bonjour le monde") == "Bonjour le monde."


def test_privacy_refusal_keeps_the_raw_text(backend):
    backend["error"] = privacy.PolicyError("remote endpoint rejected")
    assert dictation_cleanup.cleanup("euh bonjour") == "euh bonjour"


def test_backend_failure_keeps_the_raw_text(backend):
    backend["error"] = RuntimeError("connection refused")
    assert dictation_cleanup.cleanup("euh bonjour") == "euh bonjour"


def test_empty_transcript_is_never_sent_to_the_model(backend):
    assert dictation_cleanup.cleanup("") == ""
    assert dictation_cleanup.cleanup("   ") == "   "
    assert backend["calls"] == []


def test_enabled_reads_the_stored_toggle(monkeypatch):
    values = {"dictation_cleanup": "true"}
    monkeypatch.setattr(dictation_cleanup.db, "get_setting",
                        lambda key, default="": values.get(key, default))
    assert dictation_cleanup.enabled() is True
    values["dictation_cleanup"] = "false"
    assert dictation_cleanup.enabled() is False


def test_plausibility_bounds():
    assert dictation_cleanup._plausible("a" * 100, "a" * 100)
    assert not dictation_cleanup._plausible("a" * 100, "a" * 10)
    assert not dictation_cleanup._plausible("a" * 100, "a" * 500)
    assert not dictation_cleanup._plausible("a" * 100, "")


def test_no_dedicated_url_uses_the_assistant_stack(monkeypatch):
    monkeypatch.setattr(dictation_cleanup.db, "get_setting",
                        lambda key, default="": {"dictation_cleanup_url": ""}.get(key, default))
    import assistant
    sentinel = Mock()
    monkeypatch.setattr(assistant, "_get_backend", lambda: sentinel)
    backend, url = dictation_cleanup._backend()
    assert backend is sentinel
    assert url == ""


def test_a_dedicated_url_builds_its_own_backend(monkeypatch):
    values = {"dictation_cleanup_url": "http://127.0.0.1:8099",
              "dictation_cleanup_model": "qwen3-1.7b",
              "llama_model": "/models/assistant.gguf"}
    monkeypatch.setattr(dictation_cleanup.db, "get_setting",
                        lambda key, default="": values.get(key, default))
    backend, url = dictation_cleanup._backend()
    assert url == "http://127.0.0.1:8099"
    assert backend._model == "qwen3-1.7b"
    assert backend._url == "http://127.0.0.1:8099/v1/chat/completions"


def test_a_dedicated_url_without_a_model_falls_back_to_the_assistant_one(monkeypatch, tmp_path):
    for name in ("model.bin", "config.json", "tokenizer.json", "vocabulary.json"):
        (tmp_path / name).write_text("synthetic")
    model = str(tmp_path / "assistant.gguf")
    values = {"dictation_cleanup_url": "http://127.0.0.1:8099",
              "dictation_cleanup_model": "", "llama_model": model}
    monkeypatch.setattr(dictation_cleanup.db, "get_setting",
                        lambda key, default="": values.get(key, default))
    backend, _ = dictation_cleanup._backend()
    assert backend._model == model


def test_a_dedicated_url_is_never_started_by_vigil(monkeypatch):
    import llm_manager
    started = []
    monkeypatch.setattr(llm_manager.manager, "ensure_running", lambda: started.append(1))
    monkeypatch.setattr(dictation_cleanup, "_backend",
                        lambda: (Mock(chat=lambda *a, **k: reply("propre")), "http://127.0.0.1:8099"))
    assert dictation_cleanup.cleanup("euh propre") == "propre"
    assert started == []
