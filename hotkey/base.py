"""HotkeyAdapter ABC + ConfigBlockAdapter mixin for file-based compositors.

Adapters come in two flavours:
  - In-process (KDE, X11): key press routes back to a Python callback.
    set_callback(action_id, cb) wires the callback before register().
    The `command` argument to register() is informational only.
  - External (GNOME gsettings, Hyprland/Sway/niri config files): key press
    execs an argv. The adapter wires `command` (argv list) to the combo.
    set_callback() is a no-op. Trigger reaches Vigil via the D-Bus service
    (see service.py / vigil_trigger.py from Phase 0).

File-based external adapters share ConfigBlockAdapter, which manages a
fenced block inside the compositor's config file so our edits are
idempotent and uninstall leaves the file pristine.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable


_MANAGED_START = "# >>> vigil managed (do not edit) >>>"
_MANAGED_END = "# <<< vigil managed <<<"


class HotkeyAdapter(ABC):
    name: str = ""

    @abstractmethod
    def is_available(self) -> bool:
        """Quick env/binary check; False means this adapter can't bind here."""

    @abstractmethod
    def register(self, action_id: str, combo: str,
                 command: list[str] | None = None) -> bool:
        """Bind `combo` to `action_id`. Returns True on success."""

    @abstractmethod
    def unregister(self, action_id: str) -> bool:
        """Remove the binding for `action_id`. Returns True on success."""

    def set_callback(self, action_id: str, callback: Callable[[], None]) -> None:
        """Register an in-process callback. No-op for external adapters."""

    def list_registered(self) -> list[str]:
        """Return the action_ids currently bound by this adapter."""
        return []

    def shutdown(self) -> None:
        """Optional teardown (stop mainloops, release bus names)."""


class ConfigBlockAdapter(HotkeyAdapter):
    """File-based adapter that writes a fenced managed block into a config.

    Subclasses override:
        _config_path()       — absolute Path to the compositor config file
        _format_binding()    — one line for the managed block
        _reload()            — optional, e.g. `hyprctl reload`
    """

    @abstractmethod
    def _config_path(self) -> Path: ...

    @abstractmethod
    def _format_binding(self, action_id: str, combo: str,
                        command: list[str]) -> str: ...

    def _reload(self) -> None:
        pass

    # ── Managed-block I/O ─────────────────────────────────────────────────

    def _read_block(self) -> dict[str, str]:
        """Return {action_id: raw_line} for lines currently in the block."""
        path = self._config_path()
        if not path.exists():
            return {}
        m = re.search(
            re.escape(_MANAGED_START) + r"\n(.*?)\n" + re.escape(_MANAGED_END),
            path.read_text(),
            re.DOTALL,
        )
        if not m:
            return {}
        out: dict[str, str] = {}
        for line in m.group(1).splitlines():
            m2 = re.search(r"# id=(\S+)\s*$", line)
            if m2:
                out[m2.group(1)] = line
        return out

    def _write_block(self, entries: dict[str, str]) -> None:
        path = self._config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        content = path.read_text() if path.exists() else ""
        body = "\n".join(entries[k] for k in sorted(entries))
        new_block = f"{_MANAGED_START}\n{body}\n{_MANAGED_END}"
        pattern = re.compile(
            re.escape(_MANAGED_START) + r"\n.*?\n" + re.escape(_MANAGED_END),
            re.DOTALL,
        )
        if pattern.search(content):
            new_content = pattern.sub(new_block, content)
        else:
            sep = "\n\n" if content and not content.endswith("\n\n") else (
                "\n" if content.endswith("\n") else "\n\n"
            )
            new_content = content + sep + new_block + "\n"
        path.write_text(new_content)

    def _remove_block(self) -> None:
        path = self._config_path()
        if not path.exists():
            return
        pattern = re.compile(
            r"\n*" + re.escape(_MANAGED_START) + r"\n.*?\n"
            + re.escape(_MANAGED_END) + r"\n*",
            re.DOTALL,
        )
        cleaned = pattern.sub("\n", path.read_text())
        path.write_text(cleaned)

    # ── HotkeyAdapter implementation ──────────────────────────────────────

    def is_available(self) -> bool:
        return True  # subclasses add binary/socket checks

    def register(self, action_id: str, combo: str,
                 command: list[str] | None = None) -> bool:
        if command is None:
            command = ["vigil-trigger", action_id]
        line = self._format_binding(action_id, combo, command)
        line = f"{line}  # id={action_id}"
        entries = self._read_block()
        entries[action_id] = line
        self._write_block(entries)
        try:
            self._reload()
        except Exception:
            return False
        return True

    def unregister(self, action_id: str) -> bool:
        entries = self._read_block()
        if action_id not in entries:
            return True
        entries.pop(action_id)
        if entries:
            self._write_block(entries)
        else:
            self._remove_block()
        try:
            self._reload()
        except Exception:
            return False
        return True

    def list_registered(self) -> list[str]:
        return list(self._read_block().keys())
