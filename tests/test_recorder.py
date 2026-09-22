from unittest.mock import Mock

import numpy as np
import pytest

import recorder


@pytest.fixture
def mic(monkeypatch):
    monkeypatch.setattr(recorder.db, 'get_setting', lambda key, default='': default)
    monkeypatch.setattr(recorder.sd, 'query_devices', lambda *args: {'default_samplerate':48000})
    monkeypatch.setattr(recorder.sd, 'check_input_settings', Mock())
    stream = Mock()
    monkeypatch.setattr(recorder.sd, 'InputStream', stream)
    monkeypatch.setattr(recorder.threading, 'Timer', Mock())
    r = recorder.Recorder()
    monkeypatch.setattr(r, '_close', Mock())
    return r, stream


def feed(r, count=160):
    r._callback(r._generation, np.ones((count, 1), dtype=np.float32), count, None, None)


def test_wrong_mode_stop_cannot_consume_audio(mic):
    r, _ = mic
    assert r.start('dictation')
    feed(r)
    assert not r.start('assistant')
    assert r.stop('assistant') is None
    assert r.recording
    assert len(r.stop('dictation')) == 160


def test_timeout_discards_and_stale_timer_cannot_stop_new_session(mic):
    r, _ = mic
    r.on_timeout = Mock()
    r.start('dictation')
    old = r._generation
    feed(r)
    r._expire(old)
    assert r.stop('dictation') is None
    r.on_timeout.assert_called_once_with('dictation')
    assert r.start('assistant')
    r._expire(old)
    assert r.owner == 'assistant'


def test_failed_open_retries_next_press(mic):
    r, stream = mic
    stream.side_effect = [OSError('disconnected'), Mock()]
    assert not r.start()
    assert r.start()
    assert stream.call_count == 2


def test_native_rate_downsampling_preserves_duration(mic, monkeypatch):
    r, _ = mic
    monkeypatch.setattr(recorder.sd, 'check_input_settings', Mock(side_effect=ValueError()))
    assert r.start()
    feed(r, 4800)
    audio = r.stop()
    assert len(audio) == 1600
    assert audio.dtype == np.float32
    assert np.allclose(audio[30:-30], 1, atol=0.01)


def test_old_stream_callback_cannot_contaminate_new_capture(mic):
    r, _ = mic
    r.start()
    old = r._generation
    r.stop()
    r.start('assistant')
    r._callback(old, np.ones((100,1)), 100, None, None)
    assert r.stop('assistant') is None


def test_unavailable_selected_device_does_not_record_default(mic, monkeypatch):
    r, stream = mic
    monkeypatch.setattr(recorder.db, 'get_setting', lambda key, default='': 'USB mic' if key=='mic_device' else default)
    monkeypatch.setattr(recorder, 'input_devices', lambda: ['Other mic'])
    assert not r.start()
    stream.assert_not_called()


def test_buffer_is_bounded_even_if_timer_is_delayed(mic):
    r, _ = mic
    r.start()
    r._limit = 100
    feed(r, 500)
    feed(r, 500)
    assert len(r.stop()) == 100
