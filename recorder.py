import threading
import numpy as np
import sounddevice as sd
import config
from logger import log


class Recorder:
    def __init__(self):
        self._frames = []
        self._stream = None
        self.recording = False
        self.on_level = None       # optional callback(rms: float) set by main
        self.on_mic_error = None   # optional callback(msg: str) set by main
        self._mic_available = True
        self._start_lock = threading.Lock()

    def _callback(self, indata, frames, time, status):
        if self.recording:
            self._frames.append(indata.copy())
            if self.on_level is not None:
                rms = float(np.sqrt(np.mean(indata ** 2)))
                self.on_level(rms)

    def start(self):
        with self._start_lock:
            if self.recording:
                return
            self.recording = True  # claim the slot atomically before releasing the lock
        if not self._mic_available:
            self.recording = False
            log.warning("Microphone not available, cannot start recording.")
            if self.on_mic_error:
                self.on_mic_error("🎤 No microphone detected")
            return
        self._frames = []
        try:
            self._stream = sd.InputStream(
                samplerate=config.SAMPLE_RATE,
                channels=1,
                dtype="float32",
                callback=self._callback,
            )
            self._stream.start()
        except (sd.PortAudioError, OSError, Exception) as exc:
            log.error("Failed to open microphone: %s", exc)
            self.recording = False
            self._stream = None
            self._mic_available = False
            if self.on_mic_error:
                self.on_mic_error("🎤 No microphone detected")

    def stop(self):
        if not self.recording:
            return None
        self.recording = False  # stops callback from appending more frames
        stream = self._stream
        self._stream = None
        if stream is not None:
            # Close in a daemon thread — stream.stop() can block indefinitely on
            # PipeWire/Wayland, which would freeze the GLib D-Bus thread.
            def _close():
                try:
                    stream.abort()  # faster than stop() — discards pending buffers immediately
                    stream.close()
                except Exception as exc:
                    log.warning("Stream close error: %s", exc)
            threading.Thread(target=_close, daemon=True).start()
        if not self._frames:
            return None
        audio = np.concatenate(self._frames, axis=0).flatten()
        return audio
