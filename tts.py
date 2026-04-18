"""TTS engine abstraction — Piper, with sounddevice playback."""

import re
from pathlib import Path
import threading
import numpy as np
import sounddevice as sd

import config
import database as db

_playing = threading.Event()

_PIPER_DIR = Path.home() / ".local" / "share" / "writher" / "tts" / "piper"

_BUILTIN_VOICES = {
    "fr": ["fr_FR-siwis-medium", "fr_FR-upmc-medium", "fr_FR-mls-medium"],
    "en": ["en_US-amy-medium", "en_US-ryan-high", "en_GB-alan-medium"],
}

_engine: str = "off"
_mode: str = "overlay"
_voice_fr: str = ""
_voice_en: str = ""
_volume: float = 1.0


def init() -> None:
    global _engine, _mode, _voice_fr, _voice_en, _volume
    _engine   = db.get_setting("tts_engine",   "off")
    _mode     = db.get_setting("tts_mode",     "overlay")
    _voice_fr = db.get_setting("tts_voice_fr", "")
    _voice_en = db.get_setting("tts_voice_en", "")
    try:
        _volume = float(db.get_setting("tts_volume", "1.0"))
    except (ValueError, TypeError):
        _volume = 1.0
    if _engine == "kokoro":
        _engine = "off"
        db.save_setting("tts_engine", "off")


def is_enabled() -> bool:
    return _mode != "off"


def list_voices(lang: str) -> list:
    if _engine == "off":
        return []
    if _engine == "piper":
        return [
            {"name": v, "engine": "piper",
             "path": str(_PIPER_DIR / f"{v}.onnx")}
            for v in _BUILTIN_VOICES.get(lang, [])
            if (_PIPER_DIR / f"{v}.onnx").exists()
        ]
    return []


_URL_RE = re.compile(r"https?://\S+")


def _strip_urls(text: str) -> str:
    return _URL_RE.sub("", text).strip()


def speak(text: str) -> None:
    if _engine == "off" or _mode not in ("tts", "both"):
        return
    lang = config.LANGUAGE
    voice = _voice_fr if lang == "fr" else _voice_en
    _speak_piper(_strip_urls(text), voice, _volume)


def stop() -> None:
    _playing.clear()
    sd.stop()


def is_playing() -> bool:
    return _playing.is_set()


def _speak_piper(text: str, voice: str, volume: float = 1.0) -> None:
    from piper import PiperVoice
    path = _PIPER_DIR / f"{voice}.onnx"
    pv = PiperVoice.load(str(path))
    chunks = [c.audio_float_array for c in pv.synthesize(text)]
    if not chunks:
        return
    audio = np.concatenate(chunks).astype(np.float32) * volume
    _playing.set()
    sd.stop()  # flush any lingering stream (e.g. aborted recorder stream) before playing
    sd.play(audio, samplerate=pv.config.sample_rate)
    threading.Thread(target=_wait_audio_done, daemon=True).start()


def _wait_audio_done() -> None:
    sd.wait()
    _playing.clear()


def fetch_voices(lang: str) -> list:
    if _engine == "piper":
        return _fetch_piper_voices(lang)
    return []


def _fetch_piper_voices(lang: str) -> list:
    import urllib.request
    import json
    url = ("https://huggingface.co/rhasspy/piper-voices"
           "/resolve/main/voices.json")
    with urllib.request.urlopen(url) as resp:
        data = json.load(resp)
    prefix = "fr_" if lang == "fr" else "en_"
    return [
        {"name": key, "engine": "piper", "path": None}
        for key, info in data.items()
        if key.startswith(prefix)
    ]
