"""Per-compositor hotkey adapters + public HotkeyListener shim.

Public API:
    HotkeyListener(on_press_cb, on_release_cb,
                   on_assist_press_cb=None, on_assist_release_cb=None)
        .start()  → picks adapter, registers dictate + assistant bindings
        .stop()   → unregisters and releases resources

Lower-level:
    pick_adapter()            returns the HotkeyAdapter for this compositor
    HotkeyAdapter             interface base
    ConfigBlockAdapter        file-based managed-block mixin

The listener owns the press/release toggle logic (same state machine the
tray fallback uses). All adapters — in-process (KDE, X11) and external
(GNOME, Hyprland, Sway, niri) — route into the same toggle callbacks so
the behaviour is identical whether the keypress comes from KGlobalAccel,
pynput, or `vigil-trigger` shelling into the D-Bus service.
"""

from __future__ import annotations

import config
from compositor import detect as _detect
from hotkey.base import ConfigBlockAdapter, HotkeyAdapter  # noqa: F401
from logger import log


def pick_adapter() -> HotkeyAdapter:
    name = _detect()
    if name == "kde":
        from hotkey.kde import KdeAdapter
        return KdeAdapter()
    if name == "x11":
        from hotkey.x11 import X11Adapter
        return X11Adapter()
    if name == "gnome":
        from hotkey.gnome import GnomeAdapter
        return GnomeAdapter()
    if name == "hyprland":
        from hotkey.hyprland import HyprlandAdapter
        return HyprlandAdapter()
    if name == "sway":
        from hotkey.sway import SwayAdapter
        return SwayAdapter()
    if name == "niri":
        from hotkey.niri import NiriAdapter
        return NiriAdapter()
    from hotkey.manual import ManualAdapter
    return ManualAdapter()


class HotkeyListener:
    """Thin facade: picks the adapter, wires toggle callbacks, binds combos."""

    def __init__(self, on_press_cb, on_release_cb,
                 on_assist_press_cb=None, on_assist_release_cb=None):
        self._on_press = on_press_cb
        self._on_release = on_release_cb
        self._on_assist_press = on_assist_press_cb
        self._on_assist_release = on_assist_release_cb
        self._dict_rec = False
        self._assist_rec = False
        self._adapter = pick_adapter()

    @staticmethod
    def _safe_call(fn, label: str):
        try:
            fn()
        except Exception as exc:
            log.error("%s error: %s", label, exc)

    def _toggle_dictation(self):
        if not self._dict_rec:
            self._dict_rec = True
            self._safe_call(self._on_press, "Dictation toggle-start")
        else:
            self._dict_rec = False
            self._safe_call(self._on_release, "Dictation toggle-stop")

    def _toggle_assistant(self):
        if not self._assist_rec:
            self._assist_rec = True
            if self._on_assist_press:
                self._safe_call(self._on_assist_press, "Assistant toggle-start")
        else:
            self._assist_rec = False
            if self._on_assist_release:
                self._safe_call(self._on_assist_release, "Assistant toggle-stop")

    def start(self):
        a = self._adapter
        if not a.is_available():
            log.warning("Hotkey adapter %s is not available on this system.", a.name)
            return

        a.set_callback("dictate", self._toggle_dictation)
        dict_ok = a.register("dictate", config.HOTKEY,
                             command=["vigil-trigger", "dictate"])

        assist_ok = True
        if self._on_assist_press:
            a.set_callback("assistant", self._toggle_assistant)
            assist_ok = a.register("assistant", config.ASSISTANT_HOTKEY,
                                   command=["vigil-trigger", "assistant"])

        log.info(
            "Hotkeys via %s: dictate=%s (%s) assist=%s (%s)",
            a.name,
            config.HOTKEY, "ok" if dict_ok else "FAIL",
            config.ASSISTANT_HOTKEY if self._on_assist_press else "none",
            "ok" if assist_ok else ("FAIL" if self._on_assist_press else "skipped"),
        )

    def stop(self):
        a = self._adapter
        try:
            a.unregister("dictate")
            if self._on_assist_press:
                a.unregister("assistant")
        except Exception as exc:
            log.warning("Hotkey unregister error: %s", exc)
        try:
            a.shutdown()
        except Exception:
            pass
