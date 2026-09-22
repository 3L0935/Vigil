"""Offline-only speech inference; downloading is a separate explicit action."""
import os
from pathlib import Path

# Disable hub telemetry for the explicit download path as well.
os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')

import numpy as np
from faster_whisper import WhisperModel
from faster_whisper.utils import download_model

import config
from dictation import initial_prompt, recognition_language
from logger import log


class ModelUnavailable(RuntimeError):
    pass


def model_path(model: str, *, download: bool = False) -> str:
    """Resolve a complete snapshot without silently repairing it over the network."""
    try:
        path = Path(model) if Path(model).is_dir() else Path(
            download_model(model, local_files_only=not download))
        required = ['model.bin', 'config.json', 'tokenizer.json']
        if not all((path / file).is_file() and (path / file).stat().st_size > 0
                   for file in required):
            raise ModelUnavailable('Speech model cache is incomplete')
        vocabulary = list(path.glob('vocabulary.*'))
        if not any(file.is_file() and file.stat().st_size > 0 for file in vocabulary):
            raise ModelUnavailable('Speech model vocabulary is missing')
        return str(path)
    except ModelUnavailable:
        raise
    except Exception as exc:
        raise ModelUnavailable('Speech model is not available locally') from exc


class Transcriber:
    def __init__(self, model_name: str | None = None):
        path = model_path(model_name or config.MODEL_SIZE)
        log.info('Loading speech model from local disk')
        self._model = WhisperModel(path, device=config.DEVICE,
                                   compute_type=config.COMPUTE_TYPE,
                                   local_files_only=True)
        log.info('Speech model loaded')

    def transcribe(self, audio_np: np.ndarray) -> str:
        segments, _info = self._model.transcribe(
            audio_np, language=recognition_language(), initial_prompt=initial_prompt(),
            beam_size=5, vad_filter=True)
        return ' '.join(seg.text.strip() for seg in segments).strip()
