"""KDE Wayland global hotkey registration via KGlobalAccel D-Bus.

KGlobalAccel fires a single signal per key press (no release event), so
only toggle mode is supported on Wayland. Hold mode falls back gracefully.

⚠️  This module is best-effort: if KGlobalAccel is not on the session bus
(e.g. non-KDE compositor), registration silently fails and the caller should
fall back to a tray button or inform the user.
"""

import threading
from logger import log


def register(
    dictation_key: str,
    on_dictation: callable,
    assistant_key: str | None = None,
    on_assistant: callable | None = None,
) -> bool:
    """Register global hotkeys with KGlobalAccel.

    Args:
        dictation_key: Key sequence string, e.g. "ISO_Level3_Shift" or "Alt+Shift+D".
        on_dictation: Callback invoked when dictation hotkey is pressed.
        assistant_key: Optional key sequence for the assistant hotkey.
        on_assistant: Callback invoked when assistant hotkey is pressed.

    Returns:
        True if registration succeeded, False otherwise.
    """
    try:
        import dbus
        import dbus.mainloop.glib
        from gi.repository import GLib
    except ImportError:
        log.warning("dbus-python or PyGObject not installed — KGlobalAccel unavailable.")
        return False

    try:
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SessionBus()

        kga = bus.get_object("org.kde.kglobalaccel", "/kglobalaccel")
        iface = dbus.Interface(kga, dbus_interface="org.kde.KGlobalAccel")

        component = ["writher", "WritHer", "writher", ""]

        # Register dictation action
        iface.registerAction(
            component,
            ["dictate", "Start/stop dictation", dictation_key, dictation_key],
        )

        def _on_invoke(component_unique, shortcut_unique, timestamp):
            if component_unique == "writher":
                if shortcut_unique == "dictate":
                    try:
                        on_dictation()
                    except Exception as exc:
                        log.error("KGlobalAccel dictation callback error: %s", exc)
                elif shortcut_unique == "assist" and on_assistant:
                    try:
                        on_assistant()
                    except Exception as exc:
                        log.error("KGlobalAccel assistant callback error: %s", exc)

        bus.add_signal_receiver(
            _on_invoke,
            signal_name="invokeAction",
            dbus_interface="org.kde.KGlobalAccel",
        )

        if assistant_key and on_assistant:
            iface.registerAction(
                component,
                ["assist", "Start/stop assistant", assistant_key, assistant_key],
            )

        # Run GLib main loop in daemon thread for D-Bus signal delivery
        loop = GLib.MainLoop()
        t = threading.Thread(target=loop.run, daemon=True)
        t.start()

        log.info(
            "KGlobalAccel registered: dictation=%s assistant=%s",
            dictation_key,
            assistant_key or "none",
        )
        return True

    except Exception as exc:
        log.warning("KGlobalAccel registration failed: %s", exc)
        return False
