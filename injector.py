"""Inject transcribed text into the active application.

Strategy:
- Wayland: wtype (types directly via Wayland input protocol, no clipboard needed)
- X11 fallback: pyperclip + pynput Ctrl+V
If all else fails, text is saved to recovery_notes.txt.
"""

import os
import shutil
import subprocess
import time
from datetime import datetime

from platform_linux import is_wayland
from logger import log

_RECOVERY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recovery_notes.txt")


def _save_recovery(text: str):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(_RECOVERY_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {text}\n")
        log.info("Text saved to recovery_notes.txt")
    except Exception as exc:
        log.error("Failed to save recovery text: %s", exc)


def _inject_wtype(text: str) -> bool:
    """Type text via wtype (Wayland). Returns True on success."""
    if not shutil.which("wtype"):
        return False
    try:
        subprocess.run(["wtype", "--", text], check=True, timeout=5)
        log.info("Injected via wtype (%d chars)", len(text))
        return True
    except Exception as exc:
        log.warning("wtype injection failed (falling back): %s", exc)
        return False


def _inject_xdotool(text: str) -> bool:
    """Type text via xdotool (X11/XWayland). Returns True on success."""
    if not shutil.which("xdotool"):
        return False
    try:
        subprocess.run(["xdotool", "type", "--clearmodifiers", "--", text],
                       check=True, timeout=5)
        log.info("Injected via xdotool (%d chars)", len(text))
        return True
    except Exception as exc:
        log.error("xdotool injection failed: %s", exc)
        return False


def _inject_clipboard(text: str) -> bool:
    """Copy to clipboard and simulate Ctrl+V (X11). Returns True on success."""
    try:
        import pyperclip
        from pynput.keyboard import Controller, Key
        _keyboard = Controller()
        try:
            original = pyperclip.paste()
        except Exception:
            original = ""
        try:
            pyperclip.copy(text)
            time.sleep(0.05)
            with _keyboard.pressed(Key.ctrl):
                _keyboard.press("v")
                _keyboard.release("v")
            time.sleep(0.10)
            log.info("Injected via clipboard+Ctrl+V (%d chars)", len(text))
            return True
        except Exception as exc:
            log.error("Clipboard injection failed: %s", exc)
            return False
        finally:
            try:
                pyperclip.copy(original)
            except Exception:
                pass
    except ImportError:
        return False


def check_deps() -> str | None:
    """Check that at least one injection method is available.

    Returns a warning string if no method is ready, None if all is fine.
    Wayland: needs wtype (or xdotool for XWayland apps, or xclip/wl-clipboard for paste).
    X11: needs xdotool or xclip/xsel.
    """
    if is_wayland():
        has_wtype     = bool(shutil.which("wtype"))
        has_xdotool   = bool(shutil.which("xdotool"))
        has_wlclip    = bool(shutil.which("wl-copy"))
        has_xclip     = bool(shutil.which("xclip"))
        has_xsel      = bool(shutil.which("xsel"))
        has_clipboard = has_wlclip or has_xclip or has_xsel
        if has_wtype or has_xdotool or has_clipboard:
            return None
        return (
            "Dictation: no injection tool found.\n"
            "Install wtype for Wayland:  sudo pacman -S wtype\n"
            "Or xdotool for XWayland:   sudo pacman -S xdotool"
        )
    else:
        has_xdotool = bool(shutil.which("xdotool"))
        has_xclip   = bool(shutil.which("xclip"))
        has_xsel    = bool(shutil.which("xsel"))
        if has_xdotool or has_xclip or has_xsel:
            return None
        return (
            "Dictation: no injection tool found.\n"
            "Install xdotool:  sudo pacman -S xdotool\n"
            "Or xclip:         sudo pacman -S xclip"
        )


def inject(text: str):
    if not text:
        return
    if is_wayland():
        if _inject_wtype(text):
            return
        # wtype not available — fall through to xdotool (XWayland apps)
    if _inject_xdotool(text):
        return
    if _inject_clipboard(text):
        return
    log.warning("All injection methods failed — saving to recovery file")
    _save_recovery(text)
