import os


def is_wayland() -> bool:
    return bool(os.environ.get("WAYLAND_DISPLAY"))


def is_x11() -> bool:
    return bool(os.environ.get("DISPLAY")) and not is_wayland()


DISPLAY_SERVER = "wayland" if is_wayland() else "x11"
