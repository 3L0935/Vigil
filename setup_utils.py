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
    return (
        not db.get_setting("setup_complete", "")
        and not db.get_setting("llama_model", "")
    )


def find_terminal() -> str | None:
    for t in _TERMINALS:
        if shutil.which(t):
            return t
    return None


def launch_in_terminal(cmd_str: str) -> bool:
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
    try:
        subprocess.Popen(args)
    except OSError:
        return False
    return True
