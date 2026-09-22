import pytest

from dictation import apply_vocabulary, parse_vocabulary


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
