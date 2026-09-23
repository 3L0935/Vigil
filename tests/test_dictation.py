import pytest

from dictation import apply_vocabulary, apply_spoken_formatting, parse_vocabulary, postprocess


def test_longest_phrase_wins_and_replacements_do_not_cascade():
    vocab = parse_vocabulary('vigil local = Vigil Local\nvigil = WRITER\nWRITER = other')
    assert apply_vocabulary('VIGIL LOCAL et vigil', vocab) == 'Vigil Local et WRITER'


def test_whole_words_and_punctuation():
    vocab = parse_vocabulary('roque aime = ROCm\nchat = Chat')
    assert apply_vocabulary('roque aime, chats et chat.', vocab) == 'ROCm, chats et Chat.'


def test_written_form_may_contain_equals():
    assert parse_vocabulary('assign = x = 1') == {'assign': 'x = 1'}


@pytest.mark.parametrize('value', ['missing separator', '= value', 'word =', 'word = a\nWORD = b'])
def test_invalid_mapping_reports_error(value):
    with pytest.raises(ValueError):
        parse_vocabulary(value)


def test_empty_vocabulary_keeps_transcript_identical():
    assert apply_vocabulary("don't change my prose", {}) == "don't change my prose"


@pytest.mark.parametrize('spoken', ['nouvelle ligne', 'new line', 'nuova riga'])
def test_explicit_line_command_is_language_independent(spoken):
    assert apply_spoken_formatting(f'Alpha {spoken} Beta') == 'Alpha\nBeta'


@pytest.mark.parametrize('spoken', ['nouveau paragraphe', 'new paragraph', 'nuovo paragrafo'])
def test_explicit_paragraph_command(spoken):
    assert apply_spoken_formatting(f'Alpha {spoken} Beta') == 'Alpha\n\nBeta'


def test_spoken_formatting_is_opt_in_and_precedes_vocabulary(monkeypatch):
    values = {'dictation_vocabulary': 'new line = WRONG\nroque aime = ROCm',
              'dictation_spoken_formatting': 'false', 'dictation_literal_mode': 'false'}
    monkeypatch.setattr('dictation.db.get_setting', lambda key, default='': values.get(key, default))
    assert postprocess('new line and roque aime') == 'WRONG and ROCm'
    values['dictation_spoken_formatting'] = 'true'
    assert postprocess('new line and roque aime') == '\nand ROCm'
    values['dictation_literal_mode'] = 'true'
    assert postprocess('new line and roque aime') == 'WRONG and ROCm'


def test_formatting_keeps_negation_numbers_and_non_commands():
    text = "Je n'ai pas payé 1 250,50 euros. nouvelle ligne Reçu 42."
    assert apply_spoken_formatting(text) == "Je n'ai pas payé 1 250,50 euros.\nReçu 42."
    assert apply_spoken_formatting('A newline is not a command') == 'A newline is not a command'
    assert apply_spoken_formatting('Write "new line" literally') == 'Write "new line" literally'
