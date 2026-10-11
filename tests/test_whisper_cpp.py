"""whisper.cpp backend: model resolution, server lifecycle, request shape."""

from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest

import config
import transcriber
import whisper_cpp


@pytest.fixture
def installed(monkeypatch, tmp_path):
    """Pretend the binaries and one GGML model are on disk."""
    monkeypatch.setattr(whisper_cpp, "WHISPER_DIR", tmp_path)
    monkeypatch.setattr(whisper_cpp, "MODEL_DIR", tmp_path)
    server = tmp_path / "whisper-server"
    server.write_bytes(b"binary")
    server.chmod(0o755)
    model = tmp_path / "ggml-base.bin"
    model.write_bytes(b"weights")
    return tmp_path


def test_model_path_uses_local_weights(installed):
    assert whisper_cpp.model_path("base") == str(installed / "ggml-base.bin")


def test_missing_weights_fail_without_network(monkeypatch, tmp_path):
    monkeypatch.setattr(whisper_cpp, "MODEL_DIR", tmp_path)
    with pytest.raises(whisper_cpp.ModelUnavailable):
        whisper_cpp.model_path("large-v3")


def test_unknown_size_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(whisper_cpp, "MODEL_DIR", tmp_path)
    with pytest.raises(whisper_cpp.ModelUnavailable):
        whisper_cpp.model_path("large-v3-turbo")


def test_every_catalogued_model_has_a_ggml_file():
    for size in ("tiny", "base", "small", "medium", "large-v3"):
        assert whisper_cpp.MODEL_FILES[size] == f"ggml-{size}.bin"


def test_english_only_weights_are_never_selected():
    assert not any(".en." in name for name in whisper_cpp.MODEL_FILES.values())


def test_write_wav_is_16k_mono_pcm16(tmp_path):
    import wave

    target = tmp_path / "clip.wav"
    whisper_cpp.write_wav(np.linspace(-1.0, 1.0, 16000, dtype=np.float32), target)
    with wave.open(str(target)) as handle:
        assert handle.getframerate() == 16000
        assert handle.getnchannels() == 1
        assert handle.getsampwidth() == 2
        assert handle.getnframes() == 16000


def test_write_wav_clips_out_of_range_samples(tmp_path):
    import wave

    target = tmp_path / "loud.wav"
    whisper_cpp.write_wav(np.array([4.0, -4.0], dtype=np.float32), target)
    with wave.open(str(target)) as handle:
        frames = np.frombuffer(handle.readframes(2), dtype="<i2")
    assert list(frames) == [32767, -32767]


def test_gpu_switch_only_adds_the_flag_when_disabled(installed, monkeypatch):
    monkeypatch.setattr(whisper_cpp, "recognition_language", lambda: "fr")
    on = whisper_cpp.Server("base", gpu=True)
    off = whisper_cpp.Server("base", gpu=False)
    assert "-ng" not in on._command(1234)
    assert "-ng" in off._command(1234)
    assert "-l" in on._command(1234) and "fr" in on._command(1234)


def test_server_command_disables_timestamps_and_binds_loopback(installed, monkeypatch):
    monkeypatch.setattr(whisper_cpp, "recognition_language", lambda: None)
    command = whisper_cpp.Server("base", gpu=True)._command(4321)
    assert "-nt" in command
    assert command[command.index("--host") + 1] == "127.0.0.1"
    assert command[command.index("--port") + 1] == "4321"
    assert command[command.index("-l") + 1] == "auto"


def test_server_refuses_to_start_without_the_binary(monkeypatch, tmp_path):
    monkeypatch.setattr(whisper_cpp, "WHISPER_DIR", tmp_path)
    with pytest.raises(whisper_cpp.ModelUnavailable):
        whisper_cpp.Server("base").ensure_running()


def test_server_reuses_a_live_process(installed, monkeypatch):
    live = Mock()
    live.poll.return_value = None
    spawn = Mock(return_value=live)
    monkeypatch.setattr(whisper_cpp.subprocess, "Popen", spawn)
    monkeypatch.setattr(whisper_cpp.Server, "_probe", lambda self, port, deadline: True)
    server = whisper_cpp.Server("base")
    first = server.ensure_running()
    assert server.ensure_running() == first
    spawn.assert_called_once()


def test_server_restarts_after_a_dead_process(installed, monkeypatch):
    dead = Mock()
    dead.poll.return_value = 1
    spawn = Mock(return_value=dead)
    monkeypatch.setattr(whisper_cpp.subprocess, "Popen", spawn)
    monkeypatch.setattr(whisper_cpp.Server, "_probe", lambda self, port, deadline: True)
    server = whisper_cpp.Server("base")
    server.ensure_running()
    server.ensure_running()
    assert spawn.call_count == 2


def test_close_is_idempotent(installed, monkeypatch):
    live = Mock()
    live.poll.return_value = None
    monkeypatch.setattr(whisper_cpp.subprocess, "Popen", Mock(return_value=live))
    monkeypatch.setattr(whisper_cpp.Server, "_probe", lambda self, port, deadline: True)
    server = whisper_cpp.Server("base")
    server.ensure_running()
    server.close()
    server.close()
    assert live.terminate.call_count == 1


def test_transcriber_posts_the_clip_and_returns_text(installed, monkeypatch):
    import httpx

    captured = {}

    class Response:
        text = "  bonjour le monde  "

        def raise_for_status(self):
            captured["raised"] = True

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, files=None, data=None):
            captured["url"] = url
            captured["data"] = data
            captured["files"] = files
            return Response()

    monkeypatch.setattr(httpx, "Client", Client)
    monkeypatch.setattr(whisper_cpp, "initial_prompt", lambda: "")
    monkeypatch.setattr(whisper_cpp.Server, "ensure_running", lambda self: 5555)
    result = whisper_cpp.WhisperCppTranscriber("base", gpu=True).transcribe(
        np.zeros(16000, dtype=np.float32))
    assert result == "bonjour le monde"
    assert captured["url"] == "http://127.0.0.1:5555/inference"
    assert captured["data"]["response_format"] == "text"
    assert "prompt" not in captured["data"]


def test_transcriber_forwards_the_priming_prompt(installed, monkeypatch):
    import httpx

    captured = {}

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, files=None, data=None):
            captured["data"] = data
            return Mock(text="ok", raise_for_status=lambda: None)

    monkeypatch.setattr(httpx, "Client", Client)
    monkeypatch.setattr(whisper_cpp, "initial_prompt", lambda: "Vigil, ROCm")
    monkeypatch.setattr(whisper_cpp.Server, "ensure_running", lambda self: 5555)
    whisper_cpp.WhisperCppTranscriber("base").transcribe(np.zeros(160, dtype=np.float32))
    assert captured["data"]["prompt"] == "Vigil, ROCm"


def test_transcriber_removes_its_temporary_wav(installed, monkeypatch):
    import tempfile

    import httpx

    created = []
    real = tempfile.NamedTemporaryFile

    def tracked(*args, **kwargs):
        handle = real(*args, **kwargs)
        created.append(Path(handle.name))
        return handle

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, files=None, data=None):
            return Mock(text="ok", raise_for_status=lambda: None)

    monkeypatch.setattr(httpx, "Client", Client)
    monkeypatch.setattr(whisper_cpp.tempfile, "NamedTemporaryFile", tracked)
    monkeypatch.setattr(whisper_cpp, "initial_prompt", lambda: "")
    monkeypatch.setattr(whisper_cpp.Server, "ensure_running", lambda self: 5555)
    whisper_cpp.WhisperCppTranscriber("base").transcribe(np.zeros(160, dtype=np.float32))
    assert created and not created[0].exists()


def test_factory_returns_the_configured_backend(installed, monkeypatch):
    monkeypatch.setattr(config, "STT_BACKEND", "whisper_cpp")
    built = transcriber.create_transcriber("base")
    assert isinstance(built, whisper_cpp.WhisperCppTranscriber)


def test_factory_defaults_to_ctranslate(monkeypatch, tmp_path):
    for name in ("model.bin", "config.json", "tokenizer.json", "vocabulary.json"):
        (tmp_path / name).write_text("synthetic")
    monkeypatch.setattr(config, "STT_BACKEND", "faster_whisper")
    monkeypatch.setattr(transcriber, "WhisperModel", Mock(return_value=Mock()))
    assert isinstance(transcriber.create_transcriber(str(tmp_path)), transcriber.Transcriber)


def test_close_transcriber_tolerates_a_failing_backend():
    transcriber.close_transcriber(Mock(close=Mock(side_effect=RuntimeError("boom"))))
    transcriber.close_transcriber(None)


# ── The resident model has to let go of the video memory ──────────────────
# A server that never stops leaves the user closing the whole application to
# get 3.1 GB back.

def _live_server(monkeypatch, timeout):
    live = Mock()
    live.poll.return_value = None
    monkeypatch.setattr(whisper_cpp.subprocess, "Popen", Mock(return_value=live))
    monkeypatch.setattr(whisper_cpp.Server, "_probe", lambda self, port, deadline: True)
    monkeypatch.setattr(whisper_cpp.Server, "_timeout_sec", lambda self: timeout)
    return whisper_cpp.Server("base")


def test_a_dictation_arms_the_release_timer(installed, monkeypatch):
    server = _live_server(monkeypatch, 600)
    assert server._timer is None
    server.ensure_running()
    assert server._timer is not None and server._timer.is_alive()
    server.close()


def test_the_model_is_released_after_a_spell_without_dictation(installed, monkeypatch):
    import time
    released = []
    monkeypatch.setattr(whisper_cpp.Server, "close", lambda self: released.append(True))
    server = _live_server(monkeypatch, 0.8)
    server.ensure_running()
    assert released == []
    time.sleep(1.1)
    assert released == [True]


def test_a_new_dictation_postpones_the_release(installed, monkeypatch):
    import time
    released = []
    monkeypatch.setattr(whisper_cpp.Server, "close", lambda self: released.append(True))
    server = _live_server(monkeypatch, 0.8)
    server.ensure_running()
    time.sleep(0.2)
    server.ensure_running()          # the user dictates again
    time.sleep(0.7)                  # past the first deadline, before the second
    assert released == []
    time.sleep(0.5)                  # past the second
    assert released == [True]


def test_a_replaced_timer_releases_nothing(installed, monkeypatch):
    released = []
    monkeypatch.setattr(whisper_cpp.Server, "close", lambda self: released.append(True))
    server = _live_server(monkeypatch, 600)
    server.ensure_running()
    server._auto_shutdown(server._generation - 1)    # a stale timer, not the armed one
    assert released == []


def test_a_zero_timeout_keeps_the_model_loaded_for_good(monkeypatch):
    monkeypatch.setattr(whisper_cpp.Server, "_timeout_sec", lambda self: 0)
    server = whisper_cpp.Server("base")
    server._reset_timer()
    assert server._timer is None
