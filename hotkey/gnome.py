"""GNOME adapter — custom-keybindings via gsettings.

GNOME stores user-defined hotkeys as an array of relocatable-schema
paths under:
    org.gnome.settings-daemon.plugins.media-keys  custom-keybindings

Each path in the array points at a relocatable instance of:
    org.gnome.settings-daemon.plugins.media-keys.custom-keybinding
with properties `name`, `command`, `binding`.

Shelling out to gsettings keeps this adapter lightweight (no hard
PyGObject/Gio dep beyond what KGA already uses on KDE) and matches the
"gsettings call is silent" cell of the plan's support matrix.
"""

from __future__ import annotations

import re
import shlex
import shutil
import subprocess

from hotkey.base import HotkeyAdapter
from logger import log

_SCHEMA_LIST = "org.gnome.settings-daemon.plugins.media-keys"
_KEY_LIST = "custom-keybindings"
_SCHEMA_ITEM = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
_BASE_PATH = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/"


def _to_gnome_combo(combo: str) -> str:
    """Ctrl+Alt+W → <Ctrl><Alt>w (GNOME accelerator syntax)."""
    mods: list[str] = []
    key: str = ""
    for part in [p.strip() for p in combo.split("+")]:
        upper = part.upper()
        if upper == "CTRL":
            mods.append("<Ctrl>")
        elif upper == "SHIFT":
            mods.append("<Shift>")
        elif upper in ("ALT", "ALTGR"):
            mods.append("<Alt>")
        elif upper in ("META", "SUPER", "WIN"):
            mods.append("<Super>")
        elif len(part) == 1:
            key = part.lower()
        else:
            key = part
    return "".join(mods) + key


def _parse_gsettings_list(raw: str) -> list[str]:
    """Parse gsettings-get output for an `as` value into a Python list.

    Accepts any of:
      "@as []"          (explicit empty)
      "[]"              (empty)
      "['/a/']"         (single)
      "['/a/', '/b/']"  (multi)

    Handles GVariant single-quote escaping ('\\'' inside a string).
    Manual parse — ast.literal_eval would work too but is overkill and
    triggers security lints in CI.
    """
    raw = raw.strip()
    if raw.startswith("@as "):
        raw = raw[4:].strip()
    if raw in ("[]", ""):
        return []
    items = re.findall(r"'((?:[^'\\]|\\.)*)'", raw)
    return [it.replace(r"\'", "'").replace(r"\\", "\\") for it in items]


def _format_gsettings_list(items: list[str]) -> str:
    return "[" + ", ".join(f"'{p}'" for p in items) + "]"


class GnomeAdapter(HotkeyAdapter):
    name = "gnome"

    def _path_for(self, action_id: str) -> str:
        return f"{_BASE_PATH}vigil-{action_id}/"

    def _item_schema(self, action_id: str) -> str:
        return f"{_SCHEMA_ITEM}:{self._path_for(action_id)}"

    # ── HotkeyAdapter ─────────────────────────────────────────────────────

    def is_available(self) -> bool:
        return shutil.which("gsettings") is not None

    def register(self, action_id: str, combo: str,
                 command: list[str] | None = None) -> bool:
        if command is None:
            command = ["vigil-trigger", action_id]
        cmd_str = " ".join(shlex.quote(c) for c in command)
        gnome_binding = _to_gnome_combo(combo)
        schema = self._item_schema(action_id)
        path = self._path_for(action_id)

        try:
            subprocess.check_call(
                ["gsettings", "set", schema, "name", f"Vigil: {action_id}"])
            subprocess.check_call(
                ["gsettings", "set", schema, "command", cmd_str])
            subprocess.check_call(
                ["gsettings", "set", schema, "binding", gnome_binding])

            current = subprocess.check_output(
                ["gsettings", "get", _SCHEMA_LIST, _KEY_LIST], text=True)
            paths = _parse_gsettings_list(current)
            if path not in paths:
                paths.append(path)
                subprocess.check_call([
                    "gsettings", "set", _SCHEMA_LIST, _KEY_LIST,
                    _format_gsettings_list(paths),
                ])
            log.info("GNOME binding set: %s -> %s", combo, cmd_str)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            log.warning("gnome adapter: gsettings failure: %s", exc)
            return False

    def unregister(self, action_id: str) -> bool:
        schema = self._item_schema(action_id)
        path = self._path_for(action_id)
        ok = True
        try:
            current = subprocess.check_output(
                ["gsettings", "get", _SCHEMA_LIST, _KEY_LIST], text=True)
            paths = _parse_gsettings_list(current)
            if path in paths:
                paths.remove(path)
                subprocess.check_call([
                    "gsettings", "set", _SCHEMA_LIST, _KEY_LIST,
                    _format_gsettings_list(paths),
                ])
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            log.warning("gnome adapter: list-update failed: %s", exc)
            ok = False
        # Best-effort property reset (safe to ignore failures).
        for key in ("name", "command", "binding"):
            subprocess.call(["gsettings", "reset", schema, key],
                            stderr=subprocess.DEVNULL)
        return ok

    def list_registered(self) -> list[str]:
        try:
            current = subprocess.check_output(
                ["gsettings", "get", _SCHEMA_LIST, _KEY_LIST], text=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            return []
        out = []
        prefix = f"{_BASE_PATH}vigil-"
        for p in _parse_gsettings_list(current):
            if p.startswith(prefix) and p.endswith("/"):
                out.append(p[len(prefix):-1])
        return out
