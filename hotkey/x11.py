"""X11 adapter — pynput.GlobalHotKeys in a background thread."""

from __future__ import annotations

from typing import Callable

from hotkey.base import HotkeyAdapter
from logger import log


def _to_pynput_combo(combo: str) -> str:
    """Convert 'Ctrl+Alt+W' → '<ctrl>+<alt>+w' for pynput GlobalHotKeys."""
    parts = [p.strip() for p in combo.split("+")]
    result = []
    for part in parts:
        upper = part.upper()
        if upper == "CTRL":
            result.append("<ctrl>")
        elif upper == "SHIFT":
            result.append("<shift>")
        elif upper in ("ALT", "ALTGR"):
            result.append("<alt>")
        elif upper in ("META", "SUPER", "WIN"):
            result.append("<cmd>")
        elif len(part) == 1:
            result.append(part.lower())
        else:
            result.append(f"<{part.lower()}>")
    return "+".join(result)


class X11Adapter(HotkeyAdapter):
    name = "x11"

    def __init__(self):
        self._callbacks: dict[str, Callable[[], None]] = {}
        self._combos: dict[str, str] = {}  # action_id → combo
        self._listener = None

    def is_available(self) -> bool:
        try:
            from pynput.keyboard import GlobalHotKeys  # noqa: F401
            return True
        except ImportError:
            return False

    def set_callback(self, action_id: str, callback) -> None:
        self._callbacks[action_id] = callback
        if self._listener is not None:
            # Re-start with updated hotkey set.
            self._rebuild()

    def register(self, action_id: str, combo: str,
                 command: list[str] | None = None) -> bool:
        self._combos[action_id] = combo
        return self._rebuild()

    def unregister(self, action_id: str) -> bool:
        self._combos.pop(action_id, None)
        self._callbacks.pop(action_id, None)
        return self._rebuild()

    def shutdown(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    # ── Internals ────────────────────────────────────────────────────────

    def _rebuild(self) -> bool:
        try:
            from pynput.keyboard import GlobalHotKeys
        except ImportError:
            return False

        # Stop previous listener (if any) before starting a new one.
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

        hotkeys = {}
        for aid, combo in self._combos.items():
            cb = self._callbacks.get(aid)
            if cb is None:
                log.debug("X11Adapter: no callback for %s, skipping", aid)
                continue
            hotkeys[_to_pynput_combo(combo)] = cb

        if not hotkeys:
            return True  # nothing to bind

        try:
            self._listener = GlobalHotKeys(hotkeys)
            self._listener.start()
        except Exception as exc:
            log.warning("X11Adapter: GlobalHotKeys start failed: %s", exc)
            return False

        log.info("X11 hotkeys active: %s", list(hotkeys.keys()))
        return True
