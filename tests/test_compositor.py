"""Env-based compositor detection — pure logic, no side effects."""

import os
from unittest.mock import patch

import compositor


def _env(**kv):
    """Build an os.environ-shaped dict with only our keys set."""
    clean = {k: v for k, v in kv.items() if v is not None}
    return patch.dict(os.environ, clean, clear=True)


def _wayland(yes: bool):
    return patch("compositor.is_wayland", return_value=yes)


def test_x11_wins_when_not_wayland():
    with _wayland(False), _env():
        assert compositor.detect() == "x11"


def test_kde_via_full_session():
    with _wayland(True), _env(KDE_FULL_SESSION="true"):
        assert compositor.detect() == "kde"


def test_kde_via_xdg_current_desktop():
    # Plasma session can run without KDE_FULL_SESSION=true (e.g. some greeters).
    with _wayland(True), _env(XDG_CURRENT_DESKTOP="KDE"):
        assert compositor.detect() == "kde"


def test_kde_via_plasma_xdg():
    with _wayland(True), _env(XDG_CURRENT_DESKTOP="plasma"):
        assert compositor.detect() == "kde"


def test_hyprland_via_socket_env():
    with _wayland(True), _env(HYPRLAND_INSTANCE_SIGNATURE="foo_123"):
        assert compositor.detect() == "hyprland"


def test_sway_via_sock():
    with _wayland(True), _env(SWAYSOCK="/run/user/1000/sway.sock"):
        assert compositor.detect() == "sway"


def test_niri_via_socket():
    with _wayland(True), _env(NIRI_SOCKET="/run/user/1000/niri.sock"):
        assert compositor.detect() == "niri"


def test_gnome_via_xdg():
    with _wayland(True), _env(XDG_CURRENT_DESKTOP="GNOME"):
        assert compositor.detect() == "gnome"


def test_gnome_ubuntu_variant():
    with _wayland(True), _env(XDG_CURRENT_DESKTOP="ubuntu:GNOME"):
        assert compositor.detect() == "gnome"


def test_hyprland_via_xdg_without_socket():
    # Flatpak'd Hyprland may not export HYPRLAND_INSTANCE_SIGNATURE.
    with _wayland(True), _env(XDG_CURRENT_DESKTOP="Hyprland"):
        assert compositor.detect() == "hyprland"


def test_unknown_wayland_falls_back_to_wlr():
    with _wayland(True), _env(XDG_CURRENT_DESKTOP="cosmic"):
        assert compositor.detect() == "wlr"


def test_empty_wayland_env_is_wlr():
    with _wayland(True), _env():
        assert compositor.detect() == "wlr"


def test_hyprland_socket_beats_xdg_gnome():
    # Priority: specific runtime socket wins over generic XDG hint.
    with _wayland(True), _env(
        HYPRLAND_INSTANCE_SIGNATURE="sig",
        XDG_CURRENT_DESKTOP="GNOME",
    ):
        assert compositor.detect() == "hyprland"


def test_kde_beats_hyprland_sock():
    # KDE detection is first — kwin_wayland wouldn't set HYPRLAND_INSTANCE_SIGNATURE,
    # but if something weird did, KDE_FULL_SESSION should still win.
    with _wayland(True), _env(
        KDE_FULL_SESSION="true",
        HYPRLAND_INSTANCE_SIGNATURE="sig",
    ):
        assert compositor.detect() == "kde"
