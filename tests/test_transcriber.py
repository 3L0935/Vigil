from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import transcriber


@pytest.fixture
def cache(tmp_path):
    for name in ['model.bin', 'config.json', 'tokenizer.json', 'vocabulary.json']:
        (tmp_path / name).write_text('synthetic')
    return tmp_path


def test_runtime_never_downloads_and_uses_disk_path(cache, monkeypatch):
    download = Mock(return_value=str(cache))
    whisper = Mock()
    monkeypatch.setattr(transcriber, 'download_model', download)
    monkeypatch.setattr(transcriber, 'WhisperModel', whisper)
    transcriber.Transcriber('base')
    download.assert_called_once_with('base', local_files_only=True)
    assert whisper.call_args.args[0] == str(cache)
    assert whisper.call_args.kwargs['local_files_only'] is True


@pytest.mark.parametrize('missing', ['model.bin', 'config.json', 'tokenizer.json', 'vocabulary.json'])
def test_partial_cache_fails_without_network_repair(cache, monkeypatch, missing):
    (cache / missing).unlink()
    download = Mock(return_value=str(cache))
    monkeypatch.setattr(transcriber, 'download_model', download)
    with pytest.raises(transcriber.ModelUnavailable):
        transcriber.model_path('base')
    download.assert_called_once_with('base', local_files_only=True)


def test_download_requires_explicit_flag(cache, monkeypatch):
    download = Mock(return_value=str(cache))
    monkeypatch.setattr(transcriber, 'download_model', download)
    assert transcriber.model_path('base', download=True) == str(cache)
    download.assert_called_once_with('base', local_files_only=False)


def test_language_and_priming_are_independent_of_ui(cache, monkeypatch):
    import config, dictation
    monkeypatch.setattr(config, 'LANGUAGE', 'fr')
    settings = {'whisper_language':'en', 'whisper_priming':'Vigil, ROCm'}
    monkeypatch.setattr(dictation.db, 'get_setting', lambda k, d='': settings.get(k,d))
    model = Mock()
    model.transcribe.return_value = ([SimpleNamespace(text='hello')], None)
    monkeypatch.setattr(transcriber, 'WhisperModel', Mock(return_value=model))
    stt = transcriber.Transcriber(str(cache))
    assert stt.transcribe([]) == 'hello'
    assert model.transcribe.call_args.kwargs['language'] == 'en'
    assert model.transcribe.call_args.kwargs['initial_prompt'] == 'Vigil, ROCm'
    settings['whisper_language'] = 'auto'
    stt.transcribe([])
    assert model.transcribe.call_args.kwargs['language'] is None
