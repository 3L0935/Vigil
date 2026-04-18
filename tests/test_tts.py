import pytest
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _reset(engine="off", mode="overlay", vfr="", ven=""):
    import tts
    tts._engine = engine
    tts._mode = mode
    tts._voice_fr = vfr
    tts._voice_en = ven


# ── is_enabled ────────────────────────────────────────────────────────────

def test_is_enabled_off():
    _reset(mode="off")
    import tts
    assert tts.is_enabled() is False


def test_is_enabled_overlay():
    _reset(mode="overlay")
    import tts
    assert tts.is_enabled() is True


def test_is_enabled_tts():
    _reset(mode="tts")
    import tts
    assert tts.is_enabled() is True


def test_is_enabled_both():
    _reset(mode="both")
    import tts
    assert tts.is_enabled() is True


# ── init ─────────────────────────────────────────────────────────────────

def test_init_reads_db():
    import tts
    settings = {
        "tts_engine": "piper",
        "tts_mode": "both",
        "tts_voice_fr": "fr_FR-siwis-medium",
        "tts_voice_en": "en_US-ryan-high",
    }
    with patch("database.get_setting", side_effect=lambda k, d="": settings.get(k, d)):
        tts.init()
    assert tts._engine == "piper"
    assert tts._mode == "both"
    assert tts._voice_fr == "fr_FR-siwis-medium"
    assert tts._voice_en == "en_US-ryan-high"


# ── list_voices ───────────────────────────────────────────────────────────

def test_list_voices_engine_off():
    _reset(engine="off")
    import tts
    assert tts.list_voices("fr") == []
    assert tts.list_voices("en") == []


def test_list_voices_kokoro_fr():
    _reset(engine="kokoro")
    import tts
    voices = tts.list_voices("fr")
    names = [v["name"] for v in voices]
    assert "fr_0" in names
    assert all(v["engine"] == "kokoro" for v in voices)
    assert all(v["path"] is None for v in voices)


def test_list_voices_kokoro_en():
    _reset(engine="kokoro")
    import tts
    voices = tts.list_voices("en")
    names = [v["name"] for v in voices]
    assert "af_heart" in names
    assert "af_bella" in names
    assert "bm_george" in names


def test_list_voices_piper_no_files(tmp_path):
    _reset(engine="piper")
    import tts
    with patch.object(tts, "_PIPER_DIR", tmp_path):
        voices = tts.list_voices("fr")
    assert voices == []


def test_list_voices_piper_with_file(tmp_path):
    _reset(engine="piper")
    import tts
    voice_name = "fr_FR-siwis-medium"
    (tmp_path / f"{voice_name}.onnx").touch()
    with patch.object(tts, "_PIPER_DIR", tmp_path):
        voices = tts.list_voices("fr")
    assert len(voices) == 1
    assert voices[0]["name"] == voice_name
    assert voices[0]["engine"] == "piper"
    assert voices[0]["path"].endswith(f"{voice_name}.onnx")


# ── speak / stop ──────────────────────────────────────────────────────────

def test_speak_noop_when_mode_off():
    _reset(mode="off")
    import tts
    with patch("sounddevice.play") as mock_play:
        tts.speak("hello")
        mock_play.assert_not_called()


def test_speak_noop_when_mode_overlay():
    _reset(engine="piper", mode="overlay")
    import tts
    with patch("sounddevice.play") as mock_play:
        tts.speak("hello")
        mock_play.assert_not_called()


def test_speak_noop_when_engine_off():
    _reset(engine="off", mode="both")
    import tts
    with patch("sounddevice.play") as mock_play:
        tts.speak("hello")
        mock_play.assert_not_called()


def test_stop_calls_sounddevice():
    import tts
    with patch("sounddevice.stop") as mock_stop:
        tts.stop()
        mock_stop.assert_called_once()


def test_speak_piper_dispatches(monkeypatch):
    _reset(engine="piper", mode="tts", vfr="fr_FR-siwis-medium", ven="en_US-ryan-high")
    import tts
    import config as _cfg
    _cfg.LANGUAGE = "fr"
    mock_speak = MagicMock()
    monkeypatch.setattr(tts, "_speak_piper", mock_speak)
    tts.speak("bonjour")
    mock_speak.assert_called_once_with("bonjour", "fr_FR-siwis-medium")


def test_speak_kokoro_dispatches(monkeypatch):
    _reset(engine="kokoro", mode="tts", vfr="fr_0", ven="af_heart")
    import tts
    import config as _cfg
    _cfg.LANGUAGE = "en"
    mock_speak = MagicMock()
    monkeypatch.setattr(tts, "_speak_kokoro", mock_speak)
    tts.speak("hello")
    mock_speak.assert_called_once_with("hello", "af_heart", "en")


# ── fetch_voices ──────────────────────────────────────────────────────────

def test_fetch_voices_kokoro_en():
    _reset(engine="kokoro")
    import tts
    voices = tts.fetch_voices("en")
    names = [v["name"] for v in voices]
    assert "af_heart" in names
    assert all(v["engine"] == "kokoro" for v in voices)


def test_fetch_voices_engine_off():
    _reset(engine="off")
    import tts
    assert tts.fetch_voices("fr") == []


def test_fetch_voices_piper_fr(monkeypatch, tmp_path):
    _reset(engine="piper")
    import tts, json, io
    sample = {
        "fr_fr-siwis-medium": {"name": "fr_FR-siwis-medium",
                                "files": {}},
        "en_us-amy-medium":   {"name": "en_US-amy-medium",
                                "files": {}},
    }
    encoded = json.dumps(sample).encode()

    class _FakeResp:
        def read(self):
            return encoded
        def __enter__(self):
            return io.BytesIO(encoded)
        def __exit__(self, *a):
            return False

    with patch("urllib.request.urlopen", return_value=_FakeResp()):
        voices = tts.fetch_voices("fr")

    names = [v["name"] for v in voices]
    assert all("fr" in n.lower() for n in names)
    assert all("en" not in n.lower() for n in names)
