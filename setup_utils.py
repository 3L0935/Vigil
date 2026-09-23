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
    provider = db.get_setting("llm_provider", "llama_cpp")
    if provider == "llama_cpp":
        return not db.get_setting("llama_model", "")
    if provider in ("ollama_local", "ollama_cloud"):
        return not db.get_setting("ollama_model", "")
    return True


def needs_asset_repair() -> bool:
    """Open setup when an asset selected by a completed setup is missing."""
    speech_model = db.get_setting("whisper_model", "")
    if speech_model:
        from transcriber import ModelUnavailable, model_path
        try:
            model_path(speech_model)
        except ModelUnavailable:
            return True
    if db.get_setting("llm_provider", "llama_cpp") == "llama_cpp":
        return any(path and not Path(path).expanduser().is_file() for path in (
            db.get_setting("llama_model", ""), db.get_setting("llama_server_bin", ""),
        ))
    return False


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
