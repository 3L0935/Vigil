"""Launch installed applications via .desktop files."""

import re
import shlex
import subprocess
from pathlib import Path

from logger import log

_DESKTOP_DIRS = [
    Path("/usr/share/applications"),
    Path.home() / ".local" / "share" / "applications",
]

_FIELD_CODE_RE = re.compile(r'%[fFuUdDnNickvm]')


def _parse_desktop(path: Path) -> dict | None:
    cfg = {}
    try:
        for line in path.read_text(errors="replace").splitlines():
            if line.startswith('#') or '=' not in line:
                continue
            k, _, v = line.partition('=')
            cfg.setdefault(k.strip(), v.strip())
    except OSError:
        return None
    if cfg.get("Type") != "Application":
        return None
    if cfg.get("NoDisplay", "false").lower() == "true":
        return None
    if cfg.get("Terminal", "false").lower() == "true":
        return None
    name = cfg.get("Name", "")
    exec_ = _FIELD_CODE_RE.sub('', cfg.get("Exec", "")).strip()
    if not name or not exec_:
        return None
    return {"name": name, "exec": exec_}


def _list_apps() -> list[dict]:
    apps, seen = [], set()
    for d in _DESKTOP_DIRS:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.desktop")):
            app = _parse_desktop(f)
            if app and app["name"].lower() not in seen:
                seen.add(app["name"].lower())
                apps.append(app)
    return apps


def _find_app(query: str) -> dict | None:
    q = query.lower().strip()
    apps = _list_apps()
    for app in apps:
        if app["name"].lower() == q:
            return app
    for app in apps:
        if app["name"].lower().startswith(q):
            return app
    for app in apps:
        if q in app["name"].lower():
            return app
    return None


def _find_in_path(name: str) -> str | None:
    """Return full path to binary if found in PATH, else None."""
    import shutil
    return shutil.which(name.lower())


def launch(app_name: str) -> tuple[bool, str]:
    """Launch app by name. Returns (success, display_name_or_error).

    Search order:
    1. .desktop files (GUI apps)
    2. PATH binary matching the name directly
    """
    app = _find_app(app_name)
    if app:
        cmd = shlex.split(app["exec"])
        label = app["name"]
    else:
        binary = _find_in_path(app_name)
        if binary is None:
            return False, app_name
        cmd = [binary]
        label = app_name

    try:
        subprocess.Popen(
            cmd,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log.info("Launched: %s — %s", label, cmd)
        return True, label
    except Exception as exc:
        log.error("Failed to launch %s: %s", label, exc)
        return False, app_name
