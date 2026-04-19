"""vigil-trigger — tiny CLI that invokes Vigil's D-Bus Trigger method.

Used by compositor key bindings on non-KDE Wayland (GNOME custom-keybindings,
Hyprland/Sway/niri exec bindings). Short-lived, fast-startup by design —
jeepney is a pure-Python D-Bus client ~5x faster to import than dbus-python.

Usage:
    vigil-trigger <action>          action ∈ {"dictate", "assistant"}

Exit codes:
    0  sent successfully
    1  Vigil not running (no D-Bus name owner)
    2  invalid action
    3  D-Bus error
"""

import sys

_ALLOWED_ACTIONS = ("dictate", "assistant")
_BUS_NAME = "org.vigil.Service"
_OBJECT_PATH = "/org/vigil/Service"
_INTERFACE = "org.vigil.Service"


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in _ALLOWED_ACTIONS:
        print(
            f"usage: vigil-trigger {{{'|'.join(_ALLOWED_ACTIONS)}}}",
            file=sys.stderr,
        )
        return 2
    action = sys.argv[1]

    try:
        from jeepney import DBusAddress, new_method_call
        from jeepney.io.blocking import open_dbus_connection
    except ImportError:
        print("vigil-trigger: jeepney not installed in current environment",
              file=sys.stderr)
        return 3

    addr = DBusAddress(
        object_path=_OBJECT_PATH,
        bus_name=_BUS_NAME,
        interface=_INTERFACE,
    )
    msg = new_method_call(addr, "Trigger", "s", (action,))

    try:
        conn = open_dbus_connection(bus="SESSION")
    except Exception as exc:
        print(f"vigil-trigger: cannot connect to session bus: {exc}",
              file=sys.stderr)
        return 3

    try:
        reply = conn.send_and_get_reply(msg, timeout=2.0)
    except Exception as exc:
        msg_str = str(exc)
        if "NameHasNoOwner" in msg_str or "ServiceUnknown" in msg_str:
            return 1
        print(f"vigil-trigger: {exc}", file=sys.stderr)
        return 3
    finally:
        try:
            conn.close()
        except Exception:
            pass

    if reply.header.message_type.name == "error":
        err_name = reply.header.fields.get(4, "")  # HeaderFields.ERROR_NAME = 4
        if err_name in (
            "org.freedesktop.DBus.Error.ServiceUnknown",
            "org.freedesktop.DBus.Error.NameHasNoOwner",
            "org.freedesktop.DBus.Error.NoReply",
        ):
            return 1
        print(f"vigil-trigger: D-Bus error {err_name}: {reply.body}",
              file=sys.stderr)
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
