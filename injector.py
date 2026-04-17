"""Inject transcribed text into the active application using the clipboard.

Uses pyperclip for cross-platform clipboard access (xclip on X11, wl-clipboard on Wayland).
If injection fails, text is saved to recovery_notes.txt as fallback.
"""

import os
import time
from datetime import datetime

import pyperclip
from pynput.keyboard import Controller, Key
from logger import log

_RECOVERY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recovery_notes.txt")

_keyboard = Controller()


def _save_recovery(text: str):
    """Append text to recovery_notes.txt as fallback when injection fails."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(_RECOVERY_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {text}\n")
        log.info("Text saved to recovery_notes.txt")
    except Exception as exc:
        log.error("Failed to save recovery text: %s", exc)


def inject(text: str):
    """Paste *text* into the currently focused application.

    Preserves the existing clipboard content and restores it after injection.
    If clipboard write fails, text is saved to recovery_notes.txt.
    """
    if not text:
        return

    # Save current clipboard content
    try:
        original = pyperclip.paste()
    except Exception:
        original = ""

    try:
        pyperclip.copy(text)
        time.sleep(0.05)

        # Simulate Ctrl+V to paste into the active app
        with _keyboard.pressed(Key.ctrl):
            _keyboard.press("v")
            _keyboard.release("v")

        time.sleep(0.10)
    except Exception as exc:
        log.error("Clipboard injection failed: %s — saving to recovery file", exc)
        _save_recovery(text)
    finally:
        # Restore original clipboard
        try:
            pyperclip.copy(original)
        except Exception:
            pass
