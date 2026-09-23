"""Bounded, in-memory recovery for the most recent completed dictation."""

import threading
import time


class LastDictation:
    MAX_BYTES = 64 * 1024
    LIFETIME = 5 * 60

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self._raw = ""
        self._final = ""
        self._expires = 0.0
        self._timer = None
        self._generation = 0

    def store(self, raw: str, final: str, *, enabled: bool = True) -> bool:
        with self._lock:
            self._generation += 1
            if self._timer:
                self._timer.cancel()
                self._timer = None
            self._raw = self._final = ""
            self._expires = 0.0
            if not enabled or not raw or not final:
                return False
            if max(len(raw.encode("utf-8")), len(final.encode("utf-8"))) > self.MAX_BYTES:
                return False
            self._raw, self._final = raw, final
            self._expires = self._clock() + self.LIFETIME
            generation = self._generation
            self._timer = threading.Timer(self.LIFETIME, self._expire, args=(generation,))
            self._timer.daemon = True
            self._timer.start()
            return True

    def _expire(self, generation: int) -> None:
        with self._lock:
            if generation == self._generation:
                self._raw = self._final = ""
                self._expires = 0.0
                self._timer = None

    def get(self) -> tuple[str, str] | None:
        with self._lock:
            if not self._expires or self._clock() >= self._expires:
                self._raw = self._final = ""
                self._expires = 0.0
                return None
            return self._raw, self._final

    def clear(self) -> None:
        with self._lock:
            self._generation += 1
            if self._timer:
                self._timer.cancel()
                self._timer = None
            self._raw = self._final = ""
            self._expires = 0.0
