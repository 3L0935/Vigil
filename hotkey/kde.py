"""KDE Plasma adapter — KGlobalAccel D-Bus integration.

Migrated from the top-level hotkey_kglobalaccel.py. Same registration
protocol (confirmed working end-to-end with KDE Plasma 6):

  1. Pre-write desired shortcut into ~/.config/kglobalshortcutsrc so user
     customisation via System Settings survives across restarts.
  2. doRegister(action_descriptor) — creates the action in KDE.
  3. setShortcut with flag=0x1 (Autoloading) — KDE loads from the config
     we just wrote.
  4. setForeignShortcut — same call System Settings uses to activate the
     binding; this is what actually makes KWin intercept the keypress.

Per-action register()/unregister() replaces the old bulk API; each call
updates only its own key in the [vigil] section, preserving siblings.
"""

from __future__ import annotations

import configparser
import os
import threading
import time
from typing import Callable

from hotkey.base import HotkeyAdapter
from logger import log

_MOD_CTRL = 0x04000000
_MOD_SHIFT = 0x02000000
_MOD_ALT = 0x08000000
_MOD_META = 0x10000000


def _parse_combo(combo: str) -> int | None:
    """Parse 'Ctrl+Alt+W' → Qt keycode int, or None if unrecognised."""
    parts = [p.strip() for p in combo.split("+")]
    modifiers = 0
    base: int | None = None
    for part in parts:
        upper = part.upper()
        if upper == "CTRL":
            modifiers |= _MOD_CTRL
        elif upper == "SHIFT":
            modifiers |= _MOD_SHIFT
        elif upper in ("ALT", "ALTGR"):
            modifiers |= _MOD_ALT
        elif upper in ("META", "SUPER", "WIN"):
            modifiers |= _MOD_META
        elif len(part) == 1 and part.upper().isalpha():
            base = ord(part.upper())
        elif len(part) == 1 and part.isdigit():
            base = ord(part)
        elif upper.startswith("F") and upper[1:].isdigit():
            n = int(upper[1:])
            if 1 <= n <= 35:
                base = 0x01000030 + (n - 1)
        elif upper == "SPACE":
            base = 0x20
        elif upper == "TAB":
            base = 0x01000001
        elif upper in ("RETURN", "ENTER"):
            base = 0x01000005
        elif upper in ("DELETE", "DEL"):
            base = 0x01000007
        elif upper == "INSERT":
            base = 0x01000006
        elif upper == "HOME":
            base = 0x01000010
        elif upper == "END":
            base = 0x01000011
        elif upper in ("PAGEUP", "PGUP"):
            base = 0x01000016
        elif upper in ("PAGEDOWN", "PGDN"):
            base = 0x01000017
        else:
            log.warning("_parse_combo: unrecognised part '%s' in '%s'", part, combo)
            return None
    if base is None:
        log.warning("_parse_combo: no base key in '%s'", combo)
        return None
    return base | modifiers


_APP_ID = "vigil"
_KGLOBAL_CONFIG = os.path.expanduser("~/.config/kglobalshortcutsrc")

# Descriptions displayed in System Settings → Shortcuts → Vigil.
_DESCRIPTIONS = {
    "dictate": "Start/stop dictation",
    "assistant": "Start/stop assistant",
}

# Stale component IDs from earlier development names.
_STALE_SECTIONS = ("writher", "writher_test", "vigil_test", "diag")

# Actions whose name changed across versions. When an old name appears in
# kglobalshortcutsrc (pre-refactor install), KDE keeps it registered — a user
# who had bound the old name ends up with an orphan action that doesn't fire
# any callback. `_ACTION_ALIASES` routes presses of the old name to the new
# callback at runtime; `_STALE_ACTION_NAMES` lists names to purge from both
# the config file and KDE's runtime component during adapter init.
_ACTION_ALIASES = {"assist": "assistant"}
_STALE_ACTION_NAMES = ("assist",)


def _sync_one_shortcut_to_config(action_id: str, combo: str) -> None:
    """Update one key in the [vigil] section without disturbing siblings.

    KDE honours flag=0x1 (Autoloading) by reading the file here at
    doRegister time; pre-writing ensures runtime picks up our combo.
    """
    cfg = configparser.RawConfigParser(strict=False)
    cfg.optionxform = str  # preserve case
    cfg.read(_KGLOBAL_CONFIG)

    if not cfg.has_section(_APP_ID):
        cfg.add_section(_APP_ID)

    cfg.set(_APP_ID, "_k_friendly_name", "Vigil")
    cfg.set(_APP_ID, action_id, f"{combo},none,{_DESCRIPTIONS.get(action_id, action_id)}")

    for stale in _STALE_SECTIONS:
        if cfg.has_section(stale):
            cfg.remove_section(stale)

    with open(_KGLOBAL_CONFIG, "w") as f:
        cfg.write(f, space_around_delimiters=False)


class KdeAdapter(HotkeyAdapter):
    name = "kde"

    def __init__(self):
        self._callbacks: dict[str, Callable[[], None]] = {}
        self._actions: dict[str, list] = {}
        self._kga_iface = None
        self._bus = None
        self._comp_iface = None
        self._loop = None
        self._loop_thread: threading.Thread | None = None
        self._signal_connected = False
        self._stale_cleaned = False

    # ── HotkeyAdapter ─────────────────────────────────────────────────────

    def is_available(self) -> bool:
        try:
            import dbus  # noqa: F401
            from gi.repository import GLib  # noqa: F401
        except ImportError:
            return False
        # Probe: KGlobalAccel service reachable?
        try:
            import dbus as _d
            _ = _d.SessionBus().get_object("org.kde.kglobalaccel", "/kglobalaccel")
            return True
        except Exception:
            return False

    def set_callback(self, action_id: str, callback) -> None:
        self._callbacks[action_id] = callback

    def register(self, action_id: str, combo: str,
                 command: list[str] | None = None) -> bool:
        code = _parse_combo(combo)
        if code is None:
            return False

        if self._kga_iface is None and not self._init_dbus():
            return False

        if not self._stale_cleaned:
            self._release_stale_writher()
            self._purge_stale_actions()
            self._stale_cleaned = True

        _sync_one_shortcut_to_config(action_id, combo)
        time.sleep(0.15)  # let KConfig watcher pick up the file change

        import dbus
        action = [
            _APP_ID,
            action_id,
            "Vigil",
            _DESCRIPTIONS.get(action_id, action_id),
        ]
        keys = dbus.Array([dbus.Int32(code)], signature="i")
        flags = dbus.UInt32(0x1)  # Autoloading

        try:
            self._kga_iface.doRegister(action)
            self._kga_iface.setShortcut(action, keys, flags)
            self._kga_iface.setForeignShortcut(action, keys)
        except Exception as exc:
            log.warning("KGlobalAccel: register %s failed: %s", action_id, exc)
            return False

        self._actions[action_id] = action

        if not self._signal_connected:
            self._connect_signal()

        log.info("KGlobalAccel registered %s=%s", action_id, combo)
        return True

    def unregister(self, action_id: str) -> bool:
        action = self._actions.pop(action_id, None)
        if action is None or self._kga_iface is None:
            return True
        try:
            import dbus
            empty = dbus.Array([], signature="i")
            self._kga_iface.setShortcut(action, empty, dbus.UInt32(0x2))
        except Exception as exc:
            log.warning("KGlobalAccel: unregister %s error: %s", action_id, exc)
            return False
        return True

    def shutdown(self) -> None:
        for aid in list(self._actions):
            self.unregister(aid)
        if self._loop is not None and self._loop.is_running():
            self._loop.quit()

    # ── Internals ─────────────────────────────────────────────────────────

    def _init_dbus(self) -> bool:
        try:
            import dbus
            import dbus.mainloop.glib
            from gi.repository import GLib
        except ImportError as exc:
            log.warning("KGlobalAccel: missing deps: %s", exc)
            return False
        try:
            # Must pass mainloop + private=True same as service.py. Without it,
            # connect_to_signal() bombs at runtime with "connection must be
            # attached to a main loop" and KDE's keypress never reaches our
            # callback — registration succeeds, signal handler never wires,
            # shortcuts look bound but never fire. SessionBus() without
            # args may also return a cached singleton that has lost its
            # mainloop; private=True forces a fresh connection.
            mainloop = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            self._bus = dbus.SessionBus(mainloop=mainloop, private=True)
            kga_obj = self._bus.get_object("org.kde.kglobalaccel", "/kglobalaccel")
            self._kga_iface = dbus.Interface(kga_obj,
                                             dbus_interface="org.kde.KGlobalAccel")
            self._loop = GLib.MainLoop()
            t = threading.Thread(target=self._loop.run, daemon=True,
                                 name="vigil-kga-loop")
            t.start()
            self._loop_thread = t
            return True
        except Exception as exc:
            log.warning("KGlobalAccel: init failed: %s", exc)
            return False

    def _purge_stale_actions(self) -> None:
        """Clear renamed actions (e.g. 'assist' → 'assistant') from both the
        config file and KDE's runtime component. Called once per adapter
        init. Orphan entries otherwise show up as duplicate rows in System
        Settings → Shortcuts → Vigil and can steal the user's chosen combo."""
        if self._kga_iface is None or self._bus is None:
            return
        try:
            import dbus
            empty = dbus.Array([], signature="i")
            for stale_name in _STALE_ACTION_NAMES:
                desc = [_APP_ID, stale_name, "Vigil",
                        _DESCRIPTIONS.get(stale_name, stale_name)]
                try:
                    self._kga_iface.setForeignShortcut(desc, empty)
                except Exception:
                    pass
        except Exception:
            pass  # best-effort runtime purge

        # Strip stale keys from kglobalshortcutsrc so the next KConfig reload
        # doesn't resurrect them.
        try:
            cfg = configparser.RawConfigParser(strict=False)
            cfg.optionxform = str
            cfg.read(_KGLOBAL_CONFIG)
            if cfg.has_section(_APP_ID):
                changed = False
                for stale_name in _STALE_ACTION_NAMES:
                    if cfg.has_option(_APP_ID, stale_name):
                        cfg.remove_option(_APP_ID, stale_name)
                        changed = True
                        log.info("KGlobalAccel: purged stale action '%s'", stale_name)
                if changed:
                    with open(_KGLOBAL_CONFIG, "w") as f:
                        cfg.write(f, space_around_delimiters=False)
        except Exception as exc:
            log.warning("KGlobalAccel: stale-action config purge failed: %s", exc)

    def _release_stale_writher(self) -> None:
        """Empty + cleanUp() legacy 'writher' component so KDE doesn't
        re-claim our combos on its next kglobalshortcutsrc rewrite."""
        if self._kga_iface is None or self._bus is None:
            return
        try:
            import dbus
            old_path = str(self._kga_iface.getComponent("writher"))
            old_obj = self._bus.get_object("org.kde.kglobalaccel", old_path)
            old_iface = dbus.Interface(
                old_obj, dbus_interface="org.kde.kglobalaccel.Component")
            empty = dbus.Array([], signature="i")
            for action_name in old_iface.shortcutNames():
                stale = ["writher", str(action_name), "writher", str(action_name)]
                try:
                    self._kga_iface.setForeignShortcut(stale, empty)
                except Exception:
                    pass
            old_iface.cleanUp()
            time.sleep(0.2)
            log.info("KGlobalAccel: released stale 'writher' component")
        except Exception:
            pass  # legacy component absent — fine

    def _connect_signal(self) -> None:
        if self._kga_iface is None or self._bus is None:
            return
        try:
            import dbus
            comp_path = str(self._kga_iface.getComponent(_APP_ID))
            comp_obj = self._bus.get_object("org.kde.kglobalaccel", comp_path)
            self._comp_iface = dbus.Interface(
                comp_obj, dbus_interface="org.kde.kglobalaccel.Component")
            self._comp_iface.connect_to_signal(
                "globalShortcutPressed", self._on_pressed)
            self._signal_connected = True
            log.info("KGlobalAccel component path: %s", comp_path)
        except Exception as exc:
            log.warning("KGlobalAccel: signal connect failed: %s", exc)

    def _on_pressed(self, component_unique, shortcut_unique, timestamp):
        name = str(shortcut_unique)
        log.debug("KGlobalAccel: pressed component=%s shortcut=%s",
                  component_unique, name)
        # Route legacy names (e.g. "assist") to the current callback
        # ("assistant") so users upgrading from pre-refactor installs don't
        # lose their hotkey even before _purge_stale_actions cleans KDE.
        resolved = _ACTION_ALIASES.get(name, name)
        cb = self._callbacks.get(resolved)
        if cb is None:
            return
        try:
            cb()
        except Exception as exc:
            log.error("KGlobalAccel callback error: %s", exc)
