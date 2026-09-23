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


class DictationSessions:
    """Serialize cancellation and the point where injection becomes irreversible."""

    def __init__(self):
        self._lock = threading.Lock()
        self._generation = 0
        self._active = 0
        self._phase = "idle"
        self._retain = True

    def start(self) -> int:
        with self._lock:
            self._generation += 1
            self._active = self._generation
            self._phase = "recording"
            self._retain = True
            return self._active

    def active_id(self) -> int:
        with self._lock:
            return self._active

    def queue(self, session: int) -> bool:
        with self._lock:
            if session != self._active or self._phase != "recording":
                return False
            self._phase = "queued"
            return True

    def processing(self, session: int) -> bool:
        with self._lock:
            if session != self._active or self._phase != "queued":
                return False
            self._phase = "processing"
            return True

    def begin_injection(self, session: int) -> bool:
        with self._lock:
            if session != self._active or self._phase not in ("processing", "preview"):
                return False
            self._phase = "injecting"
            return True

    def preview(self, session: int) -> bool:
        with self._lock:
            if session != self._active or self._phase != "processing":
                return False
            self._phase = "preview"
            return True

    def is_preview(self, session: int) -> bool:
        with self._lock:
            return session == self._active and self._phase == "preview"

    def may_publish(self, session: int) -> bool:
        with self._lock:
            return session == self._active and self._phase in ("processing", "preview", "injecting")

    def retention_allowed(self, session: int) -> bool:
        with self._lock:
            return session == self._active and self._retain

    def suppress_retention(self) -> None:
        with self._lock:
            self._retain = False

    def cancel(self) -> str:
        with self._lock:
            if self._phase == "idle":
                return "none"
            if self._phase == "injecting":
                return "too_late"
            self._active = 0
            self._phase = "idle"
            self._retain = False
            return "cancelled"

    def finish(self, session: int) -> None:
        with self._lock:
            if session == self._active:
                self._active = 0
                self._phase = "idle"
                self._retain = False
