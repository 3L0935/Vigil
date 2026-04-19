"""D-Bus service for Vigil — exposes Trigger(action) for external invocation.

External callers (vigil-trigger CLI, compositor key bindings on non-KDE
Wayland) send:
    org.vigil.Service.Trigger(action)   # action ∈ {"dictate", "assistant"}

The session-bus name also acts as a single-instance lock: a second Vigil
instance fails to claim the name and the caller can exit cleanly.
"""

import threading
from logger import log

_BUS_NAME = "org.vigil.Service"
_OBJECT_PATH = "/org/vigil/Service"
_INTERFACE = "org.vigil.Service"

_ALLOWED_ACTIONS = ("dictate", "assistant")

_state: dict = {}


def is_running() -> bool:
    """Cheap probe: is another Vigil already holding the bus name?

    Used at startup to fail fast before heavy init (whisper load, widget,
    tray). Does NOT claim the name itself.
    """
    try:
        import dbus
        bus = dbus.SessionBus()
        return _BUS_NAME in [str(n) for n in bus.list_names()]
    except Exception:
        return False


def start(on_dictate, on_assistant) -> bool:
    """Claim the bus name and start dispatching Trigger calls.

    Returns False if another instance already owns the name or D-Bus is
    unavailable; True on success.
    """
    try:
        import dbus
        import dbus.mainloop.glib
        import dbus.service
        from gi.repository import GLib
    except ImportError as exc:
        log.warning("D-Bus service unavailable (missing deps): %s", exc)
        return False

    # Attach a GLib mainloop to the connection. dbus.service.Object export
    # requires the connection itself to have a mainloop. SessionBus() is a
    # singleton and silently ignores `mainloop=` if a cached connection
    # already exists (e.g. from PyGObject imports); use `private=True` to
    # force a fresh connection with our mainloop attached.
    mainloop = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus(mainloop=mainloop, private=True)

    try:
        reply = bus.request_name(_BUS_NAME, dbus.bus.NAME_FLAG_DO_NOT_QUEUE)
    except Exception as exc:
        log.warning("D-Bus request_name failed: %s", exc)
        return False

    if reply == dbus.bus.REQUEST_NAME_REPLY_EXISTS:
        log.info("Bus name %s already owned — another Vigil is running.", _BUS_NAME)
        return False
    if reply != dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER:
        log.warning("Unexpected request_name reply: %s", reply)
        return False

    callbacks = {
        "dictate": on_dictate,
        "assistant": on_assistant,
    }

    class _Service(dbus.service.Object):
        def __init__(self, conn, path):
            super().__init__(conn, path)

        @dbus.service.method(_INTERFACE, in_signature="s", out_signature="")
        def Trigger(self, action):
            cb = callbacks.get(str(action))
            if cb is None:
                log.warning("D-Bus Trigger: unknown action %r", action)
                return
            log.debug("D-Bus Trigger: %s", action)
            try:
                cb()
            except Exception as exc:
                log.error("D-Bus Trigger callback error (%s): %s", action, exc)

    svc = _Service(bus, _OBJECT_PATH)

    loop = GLib.MainLoop()
    t = threading.Thread(target=loop.run, daemon=True, name="vigil-dbus-loop")
    t.start()

    _state["bus"] = bus
    _state["service"] = svc
    _state["loop"] = loop

    log.info("D-Bus service ready: %s on %s", _BUS_NAME, _OBJECT_PATH)
    return True


def stop():
    """Release the bus name and quit the GLib loop."""
    loop = _state.get("loop")
    bus = _state.get("bus")
    if loop is not None and loop.is_running():
        loop.quit()
    if bus is not None:
        try:
            bus.release_name(_BUS_NAME)
        except Exception:
            pass
    _state.clear()
