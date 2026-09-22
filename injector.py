"""Inject transcribed text into the active application.

Strategy:
- Wayland: wtype (types directly via Wayland input protocol, no clipboard needed)
- Clipboard fallback: Qt MIME snapshot + pynput Ctrl+V
If all else fails, bounded recovery uses the private XDG data directory.
"""

import shutil
import subprocess

from platform_linux import is_wayland
from logger import log


def _inject_wtype(text: str) -> bool:
    """Type text via wtype (Wayland). Returns True on success."""
    if not shutil.which("wtype"):
        return False
    try:
        subprocess.run(["wtype", "--", text], check=True, timeout=5)
        log.info("Injected via wtype (%d chars)", len(text))
        return True
    except Exception as exc:
        log.warning("wtype injection failed (falling back): %s", type(exc).__name__)
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
        log.error("xdotool injection failed: %s", type(exc).__name__)
        return False


def _inject_clipboard(text: str) -> bool:
    from clipboard_bridge import inject as clipboard_inject
    return clipboard_inject(text)


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


def prewarm() -> None:
    """Trigger the KDE Wayland Fake-Input permission prompt at startup.

    On Plasma 6 Wayland, the first time a process tries to synthesise a
    keystroke (via wtype's virtual-keyboard protocol or xdotool's XWayland
    XTEST), KWin pops a 'Une application demande des privilèges spéciaux'
    dialog and the keystroke is dropped until the user clicks OK. By
    issuing one no-op call at startup, we surface that prompt while the
    user is already waiting for the app to come up — the first real
    dictation then types immediately instead of getting silently swallowed.

    Payload: release modifiers (no-op when none are held). Choosing this
    over `wtype ""` because empty-string wtype calls are silently rejected
    by the protocol on some compositor versions, while -m release always
    reaches the permission gate. Fire-and-forget.
    """
    if not is_wayland():
        return
    cmd: list[str] | None = None
    if shutil.which("wtype"):
        cmd = ["wtype", "-m", "ctrl", "-m", "alt", "-m", "shift", "-m", "logo"]
    elif shutil.which("xdotool"):
        cmd = ["xdotool", "keyup", "ctrl", "keyup", "alt",
               "keyup", "shift", "keyup", "super"]
    if cmd is None:
        return
    try:
        subprocess.run(cmd, check=False,
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL,
                       timeout=2)
        log.info("Injector prewarm: triggered Wayland input permission prompt")
    except Exception as exc:
        log.debug("Injector prewarm skipped (%s)", exc)


def inject(text: str) -> str:
    """Return pasted / recovered / failed so the UI reports the actual outcome."""
    if not text:
        return "failed"
    if is_wayland() and _inject_wtype(text):
        return "pasted"
    if _inject_xdotool(text) or _inject_clipboard(text):
        return "pasted"
    log.warning("All injection methods failed")
    import recovery
    try:
        return "recovered" if recovery.save(text) else "failed"
    except OSError as exc:
        log.error("Recovery write failed: %s", type(exc).__name__)
        return "failed"
