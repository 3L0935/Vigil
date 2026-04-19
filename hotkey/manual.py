"""Manual fallback adapter — prints instructions for unsupported compositors.

Used for generic wlroots sessions, COSMIC, labwc, etc. where we have no
automated registration path. register() always returns False so callers
know it's the user's responsibility to bind the hotkey; the log message
tells them exactly what to bind to.
"""

from __future__ import annotations

from hotkey.base import HotkeyAdapter
from logger import log


class ManualAdapter(HotkeyAdapter):
    name = "manual"

    def is_available(self) -> bool:
        return True  # always "available" — it never actually binds

    def register(self, action_id: str, combo: str,
                 command: list[str] | None = None) -> bool:
        if command is None:
            command = ["vigil-trigger", action_id]
        cmd_str = " ".join(command)
        log.warning(
            "Vigil can't auto-bind hotkeys on this compositor. "
            "Add the following to your compositor config manually:"
        )
        log.warning("  keybind: %s", combo)
        log.warning("  command: %s", cmd_str)
        return False

    def unregister(self, action_id: str) -> bool:
        return True
