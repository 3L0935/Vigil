"""Validated dictation preferences and deterministic user vocabulary."""

import re

import database as db
import config

LANGUAGES = ('auto', 'fr', 'en', 'it')

_SPOKEN_BREAKS = {
    'nouveau paragraphe': '\n\n',
    'nouvelle ligne': '\n',
    'new paragraph': '\n\n',
    'new line': '\n',
    'nuovo paragrafo': '\n\n',
    'nuova riga': '\n',
}


def apply_spoken_formatting(text: str) -> str:
    """Replace only explicit line commands, before vocabulary replacement."""
    phrases = sorted(_SPOKEN_BREAKS, key=len, reverse=True)
    pattern = r'\s*(?<!\w)(?:' + '|'.join(re.escape(p) for p in phrases) + r')(?!\w)\s*'
    def replace(match):
        before = text[:match.start()].rstrip()
        after = text[match.end():].lstrip()
        if before.endswith(('"', '“')) or after.startswith(('"', '”')):
            return match.group()
        return _SPOKEN_BREAKS[match.group().strip().casefold()]
    return re.sub(pattern, replace, text, flags=re.IGNORECASE)


def parse_vocabulary(text: str) -> dict[str, str]:
    result = {}
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        spoken, sep, written = line.partition('=')
        spoken, written = spoken.strip().casefold(), written.strip()
        if not sep or not spoken or not written or spoken in result:
            raise ValueError(str(line_number))
        result[spoken] = written
    return result


def apply_vocabulary(text: str, vocab: dict[str, str]) -> str:
    if not vocab:
        return text
    phrases = sorted(vocab, key=len, reverse=True)
    pattern = r'(?<!\w)(?:' + '|'.join(re.escape(s) for s in phrases) + r')(?!\w)'
    return re.sub(pattern, lambda m: vocab[m.group().casefold()], text, flags=re.IGNORECASE)


def recognition_language() -> str | None:
    # Preserve pre-upgrade recognition until the user makes an explicit choice.
    lang = db.get_setting('whisper_language', db.get_setting('language', config.LANGUAGE))
    return lang if lang in LANGUAGES and lang != 'auto' else None


def initial_prompt() -> str | None:
    return db.get_setting('whisper_priming', '').strip() or None


def postprocess(text: str) -> str:
    if (db.get_setting('dictation_spoken_formatting', 'false') == 'true'
            and db.get_setting('dictation_literal_mode', 'false') != 'true'):
        text = apply_spoken_formatting(text)
    try:
        vocab = parse_vocabulary(db.get_setting('dictation_vocabulary', ''))
    except ValueError:
        vocab = {}  # a hand-edited invalid setting must not lose a dictation
    return apply_vocabulary(text, vocab)


def max_record_seconds() -> int:
    try:
        return max(5, min(600, int(db.get_setting('max_record_seconds', '120'))))
    except ValueError:
        return 120
