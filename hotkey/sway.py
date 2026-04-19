"""Sway adapter — managed block in ~/.config/sway/config."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from hotkey.base import ConfigBlockAdapter
from logger import log


def _to_sway_combo(combo: str) -> str:
    """Ctrl+Alt+W → Ctrl+Alt+w. Sway mods are PascalCase, key lowercase."""
    parts = [p.strip() for p in combo.split("+")]
    tokens: list[str] = []
    for part in parts:
        upper = part.upper()
        if upper == "CTRL":
            tokens.append("Ctrl")
        elif upper == "SHIFT":
            tokens.append("Shift")
        elif upper in ("ALT", "ALTGR"):
            tokens.append("Mod1")  # Sway canonical name for Alt
        elif upper in ("META", "SUPER", "WIN"):
            tokens.append("Mod4")  # Super
        elif len(part) == 1:
            tokens.append(part.lower())
        else:
            tokens.append(part)
    return "+".join(tokens)


class SwayAdapter(ConfigBlockAdapter):
    name = "sway"

    def _config_path(self) -> Path:
        # Sway reads $XDG_CONFIG_HOME/sway/config first; fall back to ~/.config.
        xdg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        return Path(xdg) / "sway" / "config"

    def _format_binding(self, action_id: str, combo: str,
                        command: list[str]) -> str:
        cmd_str = " ".join(shlex.quote(c) for c in command)
        return f"bindsym {_to_sway_combo(combo)} exec {cmd_str}"

    def is_available(self) -> bool:
        return bool(os.environ.get("SWAYSOCK")) or shutil.which("swaymsg") is not None

    def _reload(self) -> None:
        if shutil.which("swaymsg"):
            try:
                subprocess.run(["swaymsg", "reload"], check=False,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=2)
            except Exception as exc:
                log.warning("swaymsg reload failed: %s", exc)
