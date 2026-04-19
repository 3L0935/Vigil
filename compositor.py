"""Compositor detection for per-WM hotkey adapter routing.

Env-var heuristics chosen for portability:
  KDE_FULL_SESSION         — set by kstart on KDE Plasma sessions
  XDG_CURRENT_DESKTOP      — desktop-agnostic, "KDE", "GNOME", "sway", …
  HYPRLAND_INSTANCE_SIGNATURE, SWAYSOCK, NIRI_SOCKET — per-compositor runtime sockets

Returns one of:
  "x11" | "kde" | "gnome" | "hyprland" | "sway" | "niri" | "wlr"

"wlr" is the generic Wayland fallback (COSMIC, sway w/o SWAYSOCK,
labwc, …) — adapters for it fall back to the manual-instructions path.
"""

import os

from platform_linux import is_wayland


def detect() -> str:
    if not is_wayland():
        return "x11"

    xdg = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()

    if os.environ.get("KDE_FULL_SESSION") == "true" or "kde" in xdg or "plasma" in xdg:
        return "kde"

    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return "hyprland"
    if os.environ.get("SWAYSOCK"):
        return "sway"
    if os.environ.get("NIRI_SOCKET"):
        return "niri"

    if "gnome" in xdg:
        return "gnome"
    if "hyprland" in xdg:
        return "hyprland"
    if "sway" in xdg:
        return "sway"
    if "niri" in xdg:
        return "niri"

    return "wlr"
