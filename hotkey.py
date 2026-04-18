"""Dual-hotkey listener: one for dictation, one for assistant mode.

Toggle mode: first activation starts recording, second activation stops it.

X11:     pynput GlobalHotKeys — detects full combos like "Ctrl+Alt+W".
Wayland: KGlobalAccel D-Bus (KDE) — same combo strings via _parse_combo().
"""

from platform_linux import is_wayland
import config
from logger import log


def _to_pynput_combo(combo: str) -> str:
    """Convert 'Ctrl+Alt+W' → '<ctrl>+<alt>+w' for pynput GlobalHotKeys."""
    parts = [p.strip() for p in combo.split("+")]
    result = []
    for part in parts:
        upper = part.upper()
        if upper == "CTRL":
            result.append("<ctrl>")
        elif upper == "SHIFT":
            result.append("<shift>")
        elif upper in ("ALT", "ALTGR"):
            result.append("<alt>")
        elif upper in ("META", "SUPER", "WIN"):
            result.append("<cmd>")
        elif len(part) == 1:
            result.append(part.lower())
        else:
            result.append(f"<{part.lower()}>")
    return "+".join(result)


class HotkeyListener:
    def __init__(self, on_press_cb, on_release_cb,
                 on_assist_press_cb=None, on_assist_release_cb=None):
        self._on_press = on_press_cb
        self._on_release = on_release_cb
        self._on_assist_press = on_assist_press_cb
        self._on_assist_release = on_assist_release_cb
        self._dict_recording = False
        self._assist_recording = False
        self._listener = None

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
        from pynput.keyboard import GlobalHotKeys

        hotkeys = {}

        dict_combo = _to_pynput_combo(config.HOTKEY)

        def _dict_toggle():
            if not self._dict_recording:
                self._dict_recording = True
                self._safe_call(self._on_press, "Dictation toggle-start")
            else:
                self._dict_recording = False
                self._safe_call(self._on_release, "Dictation toggle-stop")

        hotkeys[dict_combo] = _dict_toggle

        if self._on_assist_press:
            asst_combo = _to_pynput_combo(config.ASSISTANT_HOTKEY)

            def _asst_toggle():
                if not self._assist_recording:
                    self._assist_recording = True
                    self._safe_call(self._on_assist_press, "Assistant toggle-start")
                else:
                    self._assist_recording = False
                    self._safe_call(self._on_assist_release, "Assistant toggle-stop")

            hotkeys[asst_combo] = _asst_toggle

        log.info("X11 hotkeys: dictate=%s assist=%s", dict_combo,
                 _to_pynput_combo(config.ASSISTANT_HOTKEY) if self._on_assist_press else "none")
        self._listener = GlobalHotKeys(hotkeys)
        self._listener.start()
        self._listener.wait()

    def _start_wayland(self):
        """Use KGlobalAccel on Wayland KDE; fall back to pynput if unavailable."""
        import hotkey_kglobalaccel as kga

        dict_key   = config.HOTKEY
        assist_key = config.ASSISTANT_HOTKEY

        def _on_dictation_toggle():
            if not self._dict_recording:
                self._dict_recording = True
                self._safe_call(self._on_press, "Dictation KGA start")
            else:
                self._dict_recording = False
                self._safe_call(self._on_release, "Dictation KGA stop")

        def _on_assistant_toggle():
            if not self._assist_recording:
                self._assist_recording = True
                if self._on_assist_press:
                    self._safe_call(self._on_assist_press, "Assistant KGA start")
            else:
                self._assist_recording = False
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
                "KGlobalAccel unavailable — falling back to pynput (may not work on Wayland)."
            )
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
