# setup_utils.py
"""Helpers for first-run detection and launching scripts in a terminal."""

import shutil
import subprocess
from pathlib import Path

import database as db

REPO_DIR = Path(__file__).parent

_TERMINALS = [
    "konsole", "gnome-terminal", "xfce4-terminal",
    "kitty", "alacritty", "tilix", "mate-terminal", "xterm",
]


def needs_first_run() -> bool:
    """Return True if neither setup_complete nor llama_model is set in DB."""
    return (
        not db.get_setting("setup_complete", "")
        and not db.get_setting("llama_model", "")
    )


def find_terminal() -> str | None:
    """Return the name of the first available terminal emulator, or None."""
    for t in _TERMINALS:
        if shutil.which(t):
            return t
    return None


def launch_in_terminal(cmd_str: str) -> bool:
    """Run cmd_str via bash -c in a detected terminal.

    Appends a 'Press Enter to close' prompt so the window stays open.
    Returns True if a terminal was found and Popen was called.
    """
    term = find_terminal()
    if not term:
        return False
    full = f'{cmd_str}; echo; read -rp "Press Enter to close..."'
    if term == "konsole":
        args = ["konsole", "-e", "bash", "-c", full]
    elif term in ("gnome-terminal", "tilix", "mate-terminal"):
        args = [term, "--", "bash", "-c", full]
    else:
        args = [term, "-e", "bash", "-c", full]
    subprocess.Popen(args)
    return True
