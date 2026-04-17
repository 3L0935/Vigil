"""KDE Wayland global hotkey registration via KGlobalAccel D-Bus.

KGlobalAccel API (confirmed via qdbus6 introspection):
  - doRegister([componentUnique, actionUnique, componentFriendly, actionFriendly])
  - setShortcut(action_descriptor, [qt_keycode_int], flags_uint)
      flag 0x1 = Autoloading: reads active shortcut from kglobalshortcutsrc at session start
      flag 0x2 = NoAutoloading: supposed to force-set, but KDE still returns its runtime value
  - setForeignShortcut(action_descriptor, [qt_keycode_int]) — no flags, no Autoloading
  - getComponent(componentUnique) -> object path
  - Signal globalShortcutPressed(componentUnique, actionUnique, timestamp)
    on component object, interface org.kde.kglobalaccel.Component

Registration pattern (confirmed working):
  1. Pre-write desired key names to kglobalshortcutsrc so user-customised shortcuts
     survive across restarts (if user changes via System Settings, file has their value).
  2. doRegister — creates the action; KDE loads the stale runtime binding.
  3. setShortcut(0x1) — KDE returns whatever it loaded (may differ from our request).
  4. setForeignShortcut — same API System Settings uses; directly overrides active binding.
     This is the call that actually makes the shortcut fire.
"""

import configparser
import os
import threading
import time
from logger import log

_state: dict = {}  # holds refs needed for cleanup

_MOD_CTRL  = 0x04000000
_MOD_SHIFT = 0x02000000
_MOD_ALT   = 0x08000000
_MOD_META  = 0x10000000

_KEY_CODES: dict[str, int] = {
    "ISO_Level3_Shift": 0x01001103,
    "Ctrl+R":           82 | _MOD_CTRL,
    "Ctrl+D":           68 | _MOD_CTRL,
    "Ctrl+Alt+D":       68 | _MOD_CTRL | _MOD_ALT,
    "Ctrl+Alt+A":       65 | _MOD_CTRL | _MOD_ALT,
    "Ctrl+Alt+W":       87 | _MOD_CTRL | _MOD_ALT,
    "Ctrl+Alt+R":       82 | _MOD_CTRL | _MOD_ALT,
    "Meta+V":           86 | _MOD_META,
    "Meta+A":           65 | _MOD_META,
}

_APP_ID = "writher"
_KGLOBAL_CONFIG = os.path.expanduser("~/.config/kglobalshortcutsrc")

# Stale component IDs from previous debug sessions — removed on each run.
_STALE_SECTIONS = ("writher_test", "diag")


def _sync_shortcuts_to_config(dict_key: str, assist_key: str | None) -> None:
    """Write desired shortcuts into kglobalshortcutsrc before registering.

    KDE honours flag=0x1 (Autoloading) by reading the active shortcut from this
    file at doRegister time. Pre-writing the correct key names ensures KDE loads
    our desired shortcuts rather than whatever stale value it had in runtime.
    """
    cfg = configparser.RawConfigParser(strict=False)
    cfg.optionxform = str  # preserve case (KDE is case-sensitive)
    cfg.read(_KGLOBAL_CONFIG)

    if not cfg.has_section(_APP_ID):
        cfg.add_section(_APP_ID)

    cfg.set(_APP_ID, "_k_friendly_name", "WritHer")
    cfg.set(_APP_ID, "dictate", f"{dict_key},none,Start/stop dictation")
    cfg.set(_APP_ID, "assist",  f"{assist_key or ''},none,Start/stop assistant")

    for stale in _STALE_SECTIONS:
        if cfg.has_section(stale):
            cfg.remove_section(stale)

    with open(_KGLOBAL_CONFIG, "w") as f:
        cfg.write(f, space_around_delimiters=False)

    log.info("KGlobalAccel config pre-written: dictate=%s assist=%s", dict_key, assist_key or "none")


def register(
    dictation_key: str,
    on_dictation,
    assistant_key: str | None = None,
    on_assistant=None,
) -> bool:
    """Register global hotkeys with KGlobalAccel.

    Returns True if registration succeeded, False otherwise.
    Shortcuts appear in System Settings → Shortcuts → WritHer and are user-configurable.
    """
    try:
        import dbus
        import dbus.mainloop.glib
        from gi.repository import GLib
    except ImportError:
        log.warning("dbus-python or PyGObject not installed — KGlobalAccel unavailable.")
        return False

    dict_code   = _KEY_CODES.get(dictation_key)
    assist_code = _KEY_CODES.get(assistant_key) if assistant_key else None

    if dict_code is None:
        log.warning("KGlobalAccel: no Qt keycode mapping for '%s'", dictation_key)
        return False

    try:
        # Pre-write desired shortcuts to config so KDE reads correct keys via Autoloading.
        _sync_shortcuts_to_config(dictation_key, assistant_key if assist_code else None)
        time.sleep(0.3)  # allow KConfig watcher to update KDE's runtime state

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SessionBus()

        kga_obj   = bus.get_object("org.kde.kglobalaccel", "/kglobalaccel")
        kga_iface = dbus.Interface(kga_obj, dbus_interface="org.kde.KGlobalAccel")

        app_name = "WritHer"

        # Parameter order: [componentUnique, actionUnique, componentFriendly, actionFriendly]
        dict_action   = [_APP_ID, "dictate", app_name, "Start/stop dictation"]
        assist_action = [_APP_ID, "assist",  app_name, "Start/stop assistant"]

        # flag=0x1 (Autoloading): KDE reads the active shortcut from the config file
        # we just wrote, ensuring the correct key is activated.
        flags = dbus.UInt32(0x1)

        keys_dict = dbus.Array([dbus.Int32(dict_code)], signature="i")
        kga_iface.doRegister(dict_action)
        kga_iface.setShortcut(dict_action, keys_dict, flags)
        kga_iface.setForeignShortcut(dict_action, keys_dict)
        log.info("KGlobalAccel registered dictate=%s", dictation_key)

        if assist_code is not None and on_assistant:
            keys_assist = dbus.Array([dbus.Int32(assist_code)], signature="i")
            kga_iface.doRegister(assist_action)
            kga_iface.setShortcut(assist_action, keys_assist, flags)
            kga_iface.setForeignShortcut(assist_action, keys_assist)
            log.info("KGlobalAccel registered assist=%s", assistant_key)

        comp_path = str(kga_iface.getComponent(_APP_ID))
        log.info("KGlobalAccel component path: %s", comp_path)

        comp_obj   = bus.get_object("org.kde.kglobalaccel", comp_path)
        comp_iface = dbus.Interface(comp_obj,
                                    dbus_interface="org.kde.kglobalaccel.Component")

        callbacks = {
            "dictate": on_dictation,
            "assist":  on_assistant,
        }

        def _on_shortcut_pressed(component_unique, shortcut_unique, timestamp):
            log.debug("KGlobalAccel: pressed component=%s shortcut=%s",
                      component_unique, shortcut_unique)
            cb = callbacks.get(str(shortcut_unique))
            if cb:
                try:
                    cb()
                except Exception as exc:
                    log.error("KGlobalAccel callback error: %s", exc)

        comp_iface.connect_to_signal("globalShortcutPressed", _on_shortcut_pressed)

        loop = GLib.MainLoop()
        t = threading.Thread(target=loop.run, daemon=True)
        t.start()

        _state["kga_iface"]    = kga_iface
        _state["dict_action"]  = dict_action
        _state["assist_action"] = assist_action if (assist_code and on_assistant) else None
        _state["loop"]         = loop

        log.info(
            "KGlobalAccel registered: dictation='%s' assistant='%s' (configurable in System Settings → Shortcuts → WritHer)",
            dictation_key, assistant_key or "none",
        )
        return True

    except Exception as exc:
        log.warning("KGlobalAccel registration failed: %s", exc)
        return False


def unregister():
    """Clear active shortcuts on exit to prevent stuck modifiers in KWin."""
    try:
        import dbus
        kga_iface = _state.get("kga_iface")
        if kga_iface is None:
            return
        empty = dbus.Array([], signature="i")
        for action_key in ("dict_action", "assist_action"):
            action = _state.get(action_key)
            if action:
                try:
                    kga_iface.setShortcut(action, empty, dbus.UInt32(0x2))
                except Exception:
                    pass
        loop = _state.get("loop")
        if loop and loop.is_running():
            loop.quit()
        log.info("KGlobalAccel shortcuts cleared.")
    except Exception as exc:
        log.warning("KGlobalAccel unregister error: %s", exc)
