"""Dual-hotkey listener: one for dictation, one for assistant mode.

Supports two recording modes controlled by config.HOLD_TO_RECORD:
  - Hold mode (True):  press=start, release=stop  (original behaviour)
  - Toggle mode (False): press=start, press again=stop  (release ignored)

On Wayland, global hotkeys are intercepted via KGlobalAccel (KDE) when available.
KGlobalAccel only fires on key press (no release), so Wayland always uses toggle mode
semantics regardless of HOLD_TO_RECORD. On X11, pynput handles both modes normally.
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

    def _is_hold_mode(self) -> bool:
        return getattr(config, "HOLD_TO_RECORD", True)

    # ── press ─────────────────────────────────────────────────────────────

    def _handle_press(self, key):
        if key == config.HOTKEY:
            if self._is_hold_mode():
                if not self._dict_pressed:
                    self._dict_pressed = True
                    self._safe_call(self._on_press, "Dictation press")
            else:
                # Toggle mode: ignore key-repeat (pressed stays True)
                if self._dict_pressed:
                    return
                self._dict_pressed = True
                if not self._dict_recording:
                    self._dict_recording = True
                    self._safe_call(self._on_press, "Dictation toggle-start")
                else:
                    self._dict_recording = False
                    self._safe_call(self._on_release, "Dictation toggle-stop")

        elif key == config.ASSISTANT_HOTKEY and self._on_assist_press:
            if self._is_hold_mode():
                if not self._assist_pressed:
                    self._assist_pressed = True
                    self._safe_call(self._on_assist_press, "Assistant press")
            else:
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
            if self._is_hold_mode():
                if self._dict_pressed:
                    self._dict_pressed = False
                    self._safe_call(self._on_release, "Dictation release")
            else:
                # Toggle mode: just reset the physical-key flag
                self._dict_pressed = False

        elif key == config.ASSISTANT_HOTKEY:
            if self._is_hold_mode():
                if self._assist_pressed and self._on_assist_release:
                    self._assist_pressed = False
                    self._safe_call(self._on_assist_release, "Assistant release")
            else:
                self._assist_pressed = False

    # ── public API to force-stop (used by timeout) ────────────────────────

    def force_stop_dictation(self):
        """Called by the timeout timer to stop a toggle-mode recording."""
        if self._dict_recording:
            self._dict_recording = False
            self._dict_pressed = False
            self._safe_call(self._on_release, "Dictation timeout-stop")

    def force_stop_assistant(self):
        """Called by the timeout timer to stop a toggle-mode recording."""
        if self._assist_recording:
            self._assist_recording = False
            self._assist_pressed = False
            if self._on_assist_release:
                self._safe_call(self._on_assist_release, "Assistant timeout-stop")

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

        # KGlobalAccel needs string key names; convert pynput Key objects
        dict_key = _key_to_str(config.HOTKEY)
        assist_key = _key_to_str(config.ASSISTANT_HOTKEY)

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
        if self._listener is not None:
            self._listener.stop()


def _key_to_str(key) -> str:
    """Convert a pynput Key or KeyCode to a KGlobalAccel-compatible string."""
    from pynput.keyboard import Key as K
    _MAP = {
        K.alt_gr: "ISO_Level3_Shift",
        K.ctrl_r: "Ctrl+Right",
        K.ctrl_l: "Ctrl+Left",
        K.alt_l: "Alt+Left",
        K.alt_r: "Alt+Right",
    }
    if key in _MAP:
        return _MAP[key]
    # KeyCode (regular key): use its char or vk
    if hasattr(key, "char") and key.char:
        return key.char.upper()
    return str(key)
