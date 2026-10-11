"""Optional LLM pass that makes a dictation read as if it had been typed.

Whisper transcribes what was said: hesitations, repetitions, and the
corrections the speaker made mid-sentence all land in the text. A short local
model pass removes them.

The pass is strictly additive. Every failure path returns the raw transcript,
because losing a dictation is far worse than keeping a filler word in it.
"""

import re

import database as db
import privacy
from logger import log, log_content

_MAX_TOKENS = 768
# A cleanup rewrites a sentence, it does not answer one. An answer, a summary
# or a truncated echo all fall outside these bounds and are discarded.
_MIN_RATIO = 0.35
_MAX_RATIO = 1.6

# Deliberately short. A long rule list makes a small model reason about the
# rules instead of applying them, which costs seconds and can exhaust the
# token budget before any text is produced.
_SYSTEM_PROMPT = """Clean up this dictated transcript:
- drop fillers and hesitations (euh, bah, ben, hmm, you know);
- drop repetitions and false starts;
- apply spoken corrections ("mardi, non en fait mercredi" becomes "mercredi");
- fix punctuation and capitalisation, and obvious misheard words;
- keep the speaker's own words, the technical terms and the numbers as they are;
- never translate, never rephrase, never add anything that was not said.

Answer in the language of the transcript, with the cleaned text only: no
quotes, no commentary, no preamble. If the transcript is already clean, return
it unchanged."""

# Honoured by the Qwen3 family, ignored by templates that do not define it.
# Models that do not use it are unaffected; models that do stop burning the
# token budget on a reasoning pass before answering.
_NO_THINKING = {"chat_template_kwargs": {"enable_thinking": False}}


def enabled() -> bool:
    return db.get_setting("dictation_cleanup", "false") == "true"


def _backend():
    """Pick the LLM stack for the cleanup pass.

    Returns ``(backend, url)``. An empty url means the assistant's own stack,
    which is the default: one model, one server, one VRAM budget. A dedicated
    URL is the escape hatch for a cleanup model of its own, because a managed
    llama-server serves exactly one model and would ignore a different name.
    """
    url = db.get_setting("dictation_cleanup_url", "").strip()
    if url:
        from llm_backend import LlamaServerBackend
        model = (db.get_setting("dictation_cleanup_model", "").strip()
                 or db.get_setting("llama_model", ""))
        return LlamaServerBackend(url, model), url
    from assistant import _get_backend
    return _get_backend(), ""


def _unwrap(text: str) -> str:
    """Drop a wrapping quote or code fence the model may have added."""
    stripped = text.strip()
    if len(stripped) > 1 and stripped[0] == stripped[-1] and stripped[0] in "\"'“”":
        return stripped[1:-1].strip()
    match = re.fullmatch(r"```[a-zA-Z]*\n(.*?)\n?```", stripped, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    return stripped


def cleanup(text: str) -> str:
    """Return a cleaned-up transcript, or the input untouched on any doubt."""
    if not text or not text.strip():
        return text
    try:
        backend, url = _backend()
        if not url:
            # Only the assistant's own server is ours to start.
            from llm_manager import manager
            manager.ensure_running()
        response = backend.chat(
            [{"role": "system", "content": _SYSTEM_PROMPT},
             {"role": "user", "content": text}],
            local_data=True, max_tokens=_MAX_TOKENS, extra=_NO_THINKING,
        )
    except privacy.PolicyError:
        log.info("Dictation cleanup skipped: endpoint refused by privacy policy")
        return text
    except Exception as exc:
        log.warning("Dictation cleanup unavailable: %s", type(exc).__name__)
        return text

    cleaned = _content(response)
    if not cleaned:
        return text
    cleaned = _unwrap(cleaned)
    if not _plausible(text, cleaned):
        log.warning("Dictation cleanup rejected: output drifted from the transcript")
        return text
    log_content("Cleaned: %r", cleaned)
    return cleaned


def _content(response) -> str:
    if not isinstance(response, dict):
        return ""
    choices = response.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        return ""
    if choices[0].get("finish_reason") == "length":
        # Truncated output would silently drop the end of the dictation.
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    return content.strip() if isinstance(content, str) else ""


def _plausible(source: str, cleaned: str) -> bool:
    if not cleaned:
        return False
    ratio = len(cleaned) / max(1, len(source))
    return _MIN_RATIO <= ratio <= _MAX_RATIO
