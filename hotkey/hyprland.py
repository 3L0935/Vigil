"""Hyprland adapter — managed block in ~/.config/hypr/hyprland.conf."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from hotkey.base import ConfigBlockAdapter
from logger import log


def _to_hyprland_combo(combo: str) -> tuple[str, str]:
    """Ctrl+Alt+W → ('CTRL ALT', 'W'). Hyprland wants mods space-separated."""
    parts = [p.strip() for p in combo.split("+")]
    mods: list[str] = []
    key: str = ""
    for part in parts:
        upper = part.upper()
        if upper == "CTRL":
            mods.append("CTRL")
        elif upper == "SHIFT":
            mods.append("SHIFT")
        elif upper in ("ALT", "ALTGR"):
            mods.append("ALT")
        elif upper in ("META", "SUPER", "WIN"):
            mods.append("SUPER")
        else:
            key = part
    return " ".join(mods), key


class HyprlandAdapter(ConfigBlockAdapter):
    name = "hyprland"

    def _config_path(self) -> Path:
        return Path(os.path.expanduser("~/.config/hypr/hyprland.conf"))

    def _format_binding(self, action_id: str, combo: str,
                        command: list[str]) -> str:
        mods, key = _to_hyprland_combo(combo)
        cmd_str = " ".join(shlex.quote(c) for c in command)
        return f"bind = {mods}, {key}, exec, {cmd_str}"

    def is_available(self) -> bool:
        return bool(os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")) \
               or shutil.which("hyprctl") is not None

    def _reload(self) -> None:
        if shutil.which("hyprctl"):
            try:
                subprocess.run(["hyprctl", "reload"], check=False,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=2)
            except Exception as exc:
                log.warning("hyprctl reload failed: %s", exc)
