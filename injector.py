"""Inject transcribed text into the active application.

Strategy:
- Wayland: wtype (types directly via the Wayland input protocol)
- Clipboard: Qt MIME snapshot + pynput Ctrl+V. This is the only path that
  carries accented characters intact on compositors without the virtual
  keyboard protocol, which is the case on KWin.
- xdotool: last resort, and only for pure-ASCII text. Typing through XTEST
  drops characters the layout cannot produce, so "plutot" arrives where
  "plutôt" was meant, silently.
If all else fails, bounded recovery uses the private XDG data directory.
"""

import shutil
import subprocess

from platform_linux import is_wayland
from logger import log

# A compositor never gains the virtual keyboard protocol while it runs, so the
# verdict is remembered: retrying only costs a doomed subprocess per dictation.
_wtype_unsupported = False


def _inject_wtype(text: str) -> bool:
    """Type text via wtype (Wayland). Returns True on success."""
    global _wtype_unsupported
    if _wtype_unsupported or not shutil.which("wtype") or not is_wayland():
        return False
    try:
        subprocess.run(["wtype", "--", text], check=True, timeout=5,
                       capture_output=True, text=True)
        log.info("Injected via wtype (%d chars)", len(text))
        return True
    except subprocess.CalledProcessError as exc:
        if "virtual keyboard protocol" in (exc.stderr or ""):
            _wtype_unsupported = True
            log.info("wtype is unusable on this compositor; using the clipboard from now on")
        else:
            log.warning("wtype injection failed (falling back): %s", type(exc).__name__)
        return False
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
    commands: list[list[str]] = []
    if shutil.which("wtype"):
        commands.append(["wtype", "-m", "ctrl", "-m", "alt", "-m", "shift", "-m", "logo"])
    if shutil.which("xdotool"):
        commands.append(["xdotool", "keyup", "ctrl", "keyup", "alt",
                         "keyup", "shift", "keyup", "super"])
    for cmd in commands:
        try:
            result = subprocess.run(cmd, check=False, timeout=2,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
        except Exception as exc:
            log.debug("Injector prewarm skipped (%s)", exc)
            continue
        if result.returncode == 0:
            log.info("Injector prewarm: triggered Wayland input permission prompt")
            return


def inject(text: str) -> str:
    """Return pasted / recovered / failed so the UI reports the actual outcome."""
    if not text:
        return "failed"
    if _inject_wtype(text):
        return "pasted"
    # xdotool is proven to reach the focused window here, but it drops some
    # accented characters. The clipboard carries them exactly, yet a paste can
    # report success without landing, so it must not pre-empt a path that
    # actually works: losing an accent is survivable, losing the dictation is not.
    if _inject_xdotool(text) or _inject_clipboard(text):
        return "pasted"
    log.warning("All injection methods failed")
    import recovery
    try:
        return "recovered" if recovery.save(text) else "failed"
    except OSError as exc:
        log.error("Recovery write failed: %s", type(exc).__name__)
        return "failed"
