"""TTS engine abstraction — Piper, with sounddevice playback."""

import json
import re
from pathlib import Path
import threading
import numpy as np
import sounddevice as sd

import config
import database as db
from logger import log

_playing = threading.Event()
_voice_cache: dict = {}
_voice_cache_lock = threading.Lock()

_PIPER_DIR = Path.home() / ".local" / "share" / "vigil" / "tts" / "piper"

_BUILTIN_VOICES = {
    "fr": ["fr_FR-siwis-medium", "fr_FR-upmc-medium", "fr_FR-mls-medium"],
    "en": ["en_US-amy-medium", "en_US-ryan-high", "en_GB-alan-medium"],
}

_engine: str = "off"
_mode: str = "overlay"
_voice_fr: str = ""
_voice_en: str = ""
_volume: float = 1.0
_speaker_fr: int = 0
_speaker_en: int = 0


def init() -> None:
    global _engine, _mode, _voice_fr, _voice_en, _volume, _speaker_fr, _speaker_en
    _engine   = db.get_setting("tts_engine",   "off")
    _mode     = db.get_setting("tts_mode",     "overlay")
    _voice_fr = db.get_setting("tts_voice_fr", "")
    _voice_en = db.get_setting("tts_voice_en", "")
    try:
        _volume = float(db.get_setting("tts_volume", "1.0"))
    except (ValueError, TypeError):
        _volume = 1.0
    try:
        _speaker_fr = int(db.get_setting("tts_speaker_fr", "0"))
    except (ValueError, TypeError):
        _speaker_fr = 0
    try:
        _speaker_en = int(db.get_setting("tts_speaker_en", "0"))
    except (ValueError, TypeError):
        _speaker_en = 0
    if _engine == "kokoro":
        _engine = "off"
        db.save_setting("tts_engine", "off")


def is_enabled() -> bool:
    return _mode != "off"


def list_voices(lang: str) -> list:
    if _engine == "off":
        return []
    if _engine == "piper":
        prefix = "fr_" if lang == "fr" else "en_"
        seen: set[str] = set()
        voices: list[dict] = []
        # Builtin voices first (preferred order)
        for v in _BUILTIN_VOICES.get(lang, []):
            if (_PIPER_DIR / f"{v}.onnx").exists():
                voices.append({"name": v, "engine": "piper",
                                "path": str(_PIPER_DIR / f"{v}.onnx")})
                seen.add(v)
        # Any other downloaded voices in the piper dir
        for f in sorted(_PIPER_DIR.glob(f"{prefix}*.onnx")):
            name = f.stem
            if name not in seen:
                voices.append({"name": name, "engine": "piper", "path": str(f)})
                seen.add(name)
        return voices
    return []


_URL_RE = re.compile(r"https?://\S+")
_TTS_MAX_CHARS = 800

_MD_SUBS = [
    (re.compile(r'!\[.*?\]\(.*?\)'),           ''),       # images → drop
    (re.compile(r'\[([^\]]+)\]\([^\)]+\)'),    r'\1'),    # [text](url) → text
    (re.compile(r'\*\*(.+?)\*\*'),             r'\1'),    # bold
    (re.compile(r'\*(.+?)\*'),                 r'\1'),    # italic
    (re.compile(r'`([^`]+)`'),                 r'\1'),    # inline code
    (re.compile(r'^#{1,6}\s+', re.MULTILINE),  ''),       # headings
    (re.compile(r'^>\s*', re.MULTILINE),       ''),       # blockquotes
    (re.compile(r'^[-*+]\s+', re.MULTILINE),   ''),       # list items
]


def _clean_for_tts(text: str) -> str:
    text = _URL_RE.sub('', text)
    for pattern, repl in _MD_SUBS:
        text = pattern.sub(repl, text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text).strip()
    if len(text) > _TTS_MAX_CHARS:
        cut = text.rfind('. ', 0, _TTS_MAX_CHARS)
        text = text[:cut + 1] if cut > _TTS_MAX_CHARS // 2 else text[:_TTS_MAX_CHARS]
    return text


def get_num_speakers(voice_name: str) -> int:
    json_path = _PIPER_DIR / f"{voice_name}.onnx.json"
    if not json_path.exists():
        return 1
    try:
        data = json.loads(json_path.read_text())
        return max(1, int(data.get("num_speakers", 1)))
    except Exception:
        return 1


def speak(text: str) -> None:
    if _engine == "off" or _mode not in ("tts", "both"):
        return
    lang = config.LANGUAGE
    voice = _voice_fr if lang == "fr" else _voice_en
    speaker_id = _speaker_fr if lang == "fr" else _speaker_en
    sid = speaker_id if get_num_speakers(voice) > 1 else None
    threading.Thread(
        target=_speak_piper,
        args=(_clean_for_tts(text), voice, _volume, sid),
        daemon=True,
    ).start()


def preview(voice_name: str, speaker_id: int | None = None) -> None:
    if _engine == "off" or _playing.is_set():
        return
    lang = "fr" if voice_name.startswith("fr_") else "en"
    sample = ("Bonjour, voici un exemple de cette voix."
              if lang == "fr" else
              "Hello, this is a sample of this voice.")
    threading.Thread(
        target=_speak_piper,
        args=(sample, voice_name, _volume, speaker_id),
        daemon=True,
    ).start()


def stop() -> None:
    _playing.clear()
    sd.stop()


def is_playing() -> bool:
    return _playing.is_set()


def _get_piper_voice(voice: str):
    """Return cached PiperVoice, loading it on first access."""
    with _voice_cache_lock:
        pv = _voice_cache.get(voice)
        if pv is not None:
            return pv
        from piper import PiperVoice
        path = _PIPER_DIR / f"{voice}.onnx"
        log.info("Loading Piper voice: %s", voice)
        pv = PiperVoice.load(str(path))
        _voice_cache[voice] = pv
        return pv


def _speak_piper(text: str, voice: str, volume: float = 1.0, speaker_id: int | None = None) -> None:
    try:
        from piper.config import SynthesisConfig
        pv = _get_piper_voice(voice)
        syn_config = SynthesisConfig(speaker_id=speaker_id) if speaker_id is not None else None
        chunks = [c.audio_float_array for c in pv.synthesize(text, syn_config=syn_config)]
        if not chunks:
            return
        audio = np.concatenate(chunks).astype(np.float32) * volume
        _playing.set()
        sd.stop()  # flush any lingering stream (e.g. aborted recorder stream) before playing
        sd.play(audio, samplerate=pv.config.sample_rate)
        threading.Thread(target=_wait_audio_done, daemon=True).start()
    except Exception as exc:
        log.error("Piper TTS error: %s", exc, exc_info=True)
        _playing.clear()


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
