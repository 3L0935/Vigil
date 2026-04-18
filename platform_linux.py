import os
import re
import subprocess


def is_wayland() -> bool:
    return bool(os.environ.get("WAYLAND_DISPLAY"))


def is_x11() -> bool:
    return bool(os.environ.get("DISPLAY")) and not is_wayland()


DISPLAY_SERVER = "wayland" if is_wayland() else "x11"


def get_xrandr_screens() -> list[str]:
    """Return list of connected xrandr output names, e.g. ['DP-2', 'DP-3', 'HDMI-A-1']."""
    try:
        out = subprocess.check_output(
            ["xrandr", "--query"], text=True, stderr=subprocess.DEVNULL, timeout=2)
        return re.findall(r"^(\S+)\s+connected\b", out, re.MULTILINE)
    except Exception:
        return []
