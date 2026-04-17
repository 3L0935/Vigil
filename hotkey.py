"""Dual-hotkey listener: one for dictation, one for assistant mode.

Toggle mode only: first press starts recording, second press stops it.

On Wayland, global hotkeys are intercepted via KGlobalAccel (KDE) when available.
KGlobalAccel only fires on key press (no release), so Wayland uses the same toggle
semantics. On X11, pynput handles press/release events normally.
"""

from platform_linux import is_wayland
from pynput import keyboard
import config
from logger import log


class HotkeyListener:
    def __init__(self, on_press_cb, on_release_cb,
                 on_assist_press_cb=None, on_assist_release_cb=None):
        self._on_press = on_press_cb
        self._on_release = on_release_cb
        self._on_assist_press = on_assist_press_cb
        self._on_assist_release = on_assist_release_cb
        self._dict_pressed = False
        self._assist_pressed = False
        # Toggle-mode state: True while actively recording
        self._dict_recording = False
        self._assist_recording = False
        self._listener = None

    # ── press ─────────────────────────────────────────────────────────────

    def _handle_press(self, key):
        if key == config.HOTKEY:
            if self._dict_pressed:
                return  # ignore key-repeat
            self._dict_pressed = True
            if not self._dict_recording:
                self._dict_recording = True
                self._safe_call(self._on_press, "Dictation toggle-start")
            else:
                self._dict_recording = False
                self._safe_call(self._on_release, "Dictation toggle-stop")

        elif key == config.ASSISTANT_HOTKEY and self._on_assist_press:
            if self._assist_pressed:
                return
            self._assist_pressed = True
            if not self._assist_recording:
                self._assist_recording = True
                self._safe_call(self._on_assist_press, "Assistant toggle-start")
            else:
                self._assist_recording = False
                self._safe_call(self._on_assist_release, "Assistant toggle-stop")

    # ── release ───────────────────────────────────────────────────────────

    def _handle_release(self, key):
        if key == config.HOTKEY:
            self._dict_pressed = False
        elif key == config.ASSISTANT_HOTKEY:
            self._assist_pressed = False

    # ── helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _safe_call(fn, label: str):
        try:
            fn()
        except Exception as exc:
            log.error("%s error: %s", label, exc)

    def start(self):
        if is_wayland():
            self._start_wayland()
        else:
            self._start_x11()

    def _start_x11(self):
        self._listener = keyboard.Listener(
            on_press=self._handle_press,
            on_release=self._handle_release,
        )
        self._listener.start()
        self._listener.wait()

    def _start_wayland(self):
        """Use KGlobalAccel on Wayland KDE; fall back gracefully if unavailable."""
        import hotkey_kglobalaccel as kga

        # Use Wayland-specific combos (modifier-only keys like AltGr/ctrl_r cannot
        # be registered with KGlobalAccel — KDE filters them at the Qt level).
        dict_key   = getattr(config, "WAYLAND_HOTKEY", "Ctrl+Alt+D")
        assist_key = getattr(config, "WAYLAND_ASSISTANT_HOTKEY", "Ctrl+Alt+A")

        # On KGlobalAccel, a single press toggles recording (no release event)
        def _on_dictation_toggle():
            if not self._dict_recording:
                self._dict_recording = True
                self._dict_pressed = True
                self._safe_call(self._on_press, "Dictation KGA start")
            else:
                self._dict_recording = False
                self._dict_pressed = False
                self._safe_call(self._on_release, "Dictation KGA stop")

        def _on_assistant_toggle():
            if not self._assist_recording:
                self._assist_recording = True
                self._assist_pressed = True
                if self._on_assist_press:
                    self._safe_call(self._on_assist_press, "Assistant KGA start")
            else:
                self._assist_recording = False
                self._assist_pressed = False
                if self._on_assist_release:
                    self._safe_call(self._on_assist_release, "Assistant KGA stop")

        success = kga.register(
            dictation_key=dict_key,
            on_dictation=_on_dictation_toggle,
            assistant_key=assist_key,
            on_assistant=_on_assistant_toggle,
        )

        if not success:
            log.warning(
                "KGlobalAccel unavailable — global hotkeys won't work on this "
                "Wayland compositor. Use the tray menu 'Start recording' instead."
            )
            # Still try pynput as last resort (may work in XWayland)
            self._start_x11()

    def stop(self):
        if is_wayland():
            try:
                import hotkey_kglobalaccel as kga
                kga.unregister()
            except Exception:
                pass
        if self._listener is not None:
            self._listener.stop()
