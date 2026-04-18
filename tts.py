"""TTS engine abstraction — Piper and Kokoro, with sounddevice playback."""

from pathlib import Path
import numpy as np
import sounddevice as sd

import config
import database as db

_PIPER_DIR = Path.home() / ".local" / "share" / "writher" / "tts" / "piper"

_BUILTIN_VOICES = {
    "piper": {
        "fr": ["fr_FR-siwis-medium", "fr_FR-upmc-medium", "fr_FR-mls-medium"],
        "en": ["en_US-amy-medium", "en_US-ryan-high", "en_GB-alan-medium"],
    },
    "kokoro": {
        "fr": ["fr_0", "fr_1", "fr_2"],
        "en": ["af_heart", "af_bella", "bm_george"],
    },
}

_engine: str = "off"
_mode: str = "overlay"
_voice_fr: str = ""
_voice_en: str = ""


def init() -> None:
    global _engine, _mode, _voice_fr, _voice_en
    _engine   = db.get_setting("tts_engine",   "off")
    _mode     = db.get_setting("tts_mode",     "overlay")
    _voice_fr = db.get_setting("tts_voice_fr", "")
    _voice_en = db.get_setting("tts_voice_en", "")


def is_enabled() -> bool:
    return _mode != "off"


def list_voices(lang: str) -> list:
    if _engine == "off":
        return []
    if _engine == "piper":
        return [
            {"name": v, "engine": "piper",
             "path": str(_PIPER_DIR / f"{v}.onnx")}
            for v in _BUILTIN_VOICES["piper"].get(lang, [])
            if (_PIPER_DIR / f"{v}.onnx").exists()
        ]
    if _engine == "kokoro":
        return [
            {"name": v, "engine": "kokoro", "path": None}
            for v in _BUILTIN_VOICES["kokoro"].get(lang, [])
        ]
    return []


def speak(text: str) -> None:
    if _engine == "off" or _mode not in ("tts", "both"):
        return
    lang = config.LANGUAGE
    voice = _voice_fr if lang == "fr" else _voice_en
    if _engine == "piper":
        _speak_piper(text, voice)
    elif _engine == "kokoro":
        _speak_kokoro(text, voice, lang)


def stop() -> None:
    sd.stop()


def _speak_piper(text: str, voice: str) -> None:
    from piper import PiperVoice
    path = _PIPER_DIR / f"{voice}.onnx"
    pv = PiperVoice.load(str(path))
    chunks = [c.audio_float_array for c in pv.synthesize(text)]
    if not chunks:
        return
    audio = np.concatenate(chunks).astype(np.float32)
    sd.play(audio, samplerate=pv.config.sample_rate)


def _speak_kokoro(text: str, voice: str, lang: str) -> None:
    from kokoro import KPipeline
    lang_code = "fr" if lang == "fr" else "en-us"
    pipeline = KPipeline(lang_code=lang_code)
    chunks = [chunk for _, _, chunk in pipeline(text, voice=voice)]
    audio = np.concatenate(chunks) if chunks else np.array([], dtype=np.float32)
    sd.play(audio, samplerate=24000)


def fetch_voices(lang: str) -> list:
    if _engine == "piper":
        return _fetch_piper_voices(lang)
    if _engine == "kokoro":
        return _fetch_kokoro_voices(lang)
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
        {"name": info.get("name", key), "engine": "piper", "path": None}
        for key, info in data.items()
        if key.startswith(prefix)
    ]


def _fetch_kokoro_voices(lang: str) -> list:
    return [
        {"name": v, "engine": "kokoro", "path": None}
        for v in _BUILTIN_VOICES["kokoro"].get(lang, [])
    ]
