"""Single-owner microphone capture with bounded sessions and hotplug recovery."""
import math
import threading

import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly

import config
import database as db
from dictation import max_record_seconds
from logger import log


def input_devices() -> list[str]:
    """Return the input devices currently exposed by PortAudio."""
    return list(dict.fromkeys(d['name'] for d in sd.query_devices()
                             if d['max_input_channels'] > 0))


class Recorder:
    def __init__(self):
        self._frames = []
        self._stream = None
        self.owner = None
        self._generation = 0
        self._lock = threading.RLock()
        self._timer = None
        self._samples = 0
        self._rate = config.SAMPLE_RATE
        self._limit = 0
        self.on_level = None
        self.on_mic_error = None
        self.on_timeout = None

    @property
    def recording(self):
        with self._lock:
            return self.owner is not None

    def _callback(self, generation, indata, frames, time, status):
        with self._lock:
            if self.owner is None or generation != self._generation:
                return
            take = min(len(indata), max(0, self._limit - self._samples))
            if take:
                self._frames.append(indata[:take].copy())
                self._samples += take
            level = self.on_level
        if level and take:
            level(float(np.sqrt(np.mean(indata[:take] ** 2))))

    def start(self, owner='dictation') -> bool:
        with self._lock:
            if self.owner is not None:
                return False
            self._generation += 1
            generation = self._generation
            self._frames = []
            self._samples = 0
            device = db.get_setting('mic_device', '').strip() or None
            try:
                if device is not None and device not in input_devices():
                    raise ValueError('selected microphone is unavailable')
                info = sd.query_devices(device, 'input')
                self._rate = config.SAMPLE_RATE
                try:
                    sd.check_input_settings(device=device, channels=1,
                                            dtype='float32', samplerate=self._rate)
                except (sd.PortAudioError, ValueError):
                    self._rate = int(info['default_samplerate'])
                seconds = max_record_seconds()
                self._limit = self._rate * seconds
                stream = sd.InputStream(
                    device=device, samplerate=self._rate, channels=1, dtype='float32',
                    callback=lambda *args: self._callback(generation, *args))
                self._stream = stream
                self.owner = owner
                stream.start()
                self._timer = threading.Timer(seconds, self._expire, args=(generation,))
                self._timer.daemon = True
                self._timer.start()
                return True
            except Exception as exc:
                stream = self._stream
                self._stream = None
                self.owner = None
                self._frames = []
                if stream:
                    self._close(stream)
                # Never latch failure: next press probes the microphone again.
                log.error('Cannot open microphone: %s', type(exc).__name__)
        if self.on_mic_error:
            import locales
            self.on_mic_error(locales.get('mic_unavailable'))
        return False

    @staticmethod
    def _close(stream):
        def close():
            try:
                stream.abort()
                stream.close()
            except Exception as exc:
                log.warning('Microphone close failed: %s', type(exc).__name__)
        threading.Thread(target=close, daemon=True).start()

    def _finish(self):
        """Detach the current session under the lock before closing its stream."""
        frames, rate = self._frames, self._rate
        self._frames = []
        self.owner = None
        self._generation += 1
        if self._timer:
            self._timer.cancel()
            self._timer = None
        stream, self._stream = self._stream, None
        if stream:
            self._close(stream)
        return frames, rate

    def _expire(self, generation):
        with self._lock:
            if generation != self._generation or self.owner is None:
                return
            owner = self.owner
            self._finish()  # discard; never send timeout audio to a worker
        if self.on_timeout:
            self.on_timeout(owner)

    def stop(self, owner=None):
        with self._lock:
            if self.owner is None or (owner is not None and owner != self.owner):
                return None
            frames, rate = self._finish()
        if not frames:
            return None
        audio = np.concatenate(frames, axis=0).flatten()
        if rate != config.SAMPLE_RATE:
            divisor = math.gcd(rate, config.SAMPLE_RATE)
            audio = resample_poly(audio, config.SAMPLE_RATE // divisor, rate // divisor)
        return audio.astype(np.float32, copy=False)
