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


def find_candidates(query: str, n: int = 4) -> list[str]:
    """Return up to n app display names that fuzzy-match query (difflib)."""
    import difflib
    q = query.lower().strip()
    apps = _list_apps()
    name_lower = [a["name"].lower() for a in apps]
    matches = difflib.get_close_matches(q, name_lower, n=n, cutoff=0.55)
    name_map = {a["name"].lower(): a["name"] for a in apps}
    return [name_map[m] for m in matches if m in name_map]


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


def _binary_from_exec(exec_str: str) -> str:
    """Extract bare binary name from an Exec string (strips path and args)."""
    try:
        return Path(shlex.split(exec_str)[0]).name
    except (ValueError, IndexError):
        return exec_str.split()[0]


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


def close(app_name: str) -> tuple[bool, str]:
    """Close a running application by name. Returns (success, label).

    Tries (in order):
    1. pkill exact match on the binary extracted from .desktop Exec
    2. pkill case-insensitive exact match on the query word
    3. pkill case-insensitive substring match
    """
    app = _find_app(app_name)
    label = app["name"] if app else app_name

    # Candidates to try: binary from .desktop first, then raw query word
    candidates: list[str] = []
    if app:
        candidates.append(_binary_from_exec(app["exec"]))
    candidates.append(app_name.lower().split()[0])  # first word, e.g. "zen" from "Zen Browser"
    candidates.append(app_name.lower())

    for name in dict.fromkeys(candidates):  # deduplicate, preserve order
        r = subprocess.run(["pkill", "-ix", name], capture_output=True)
        if r.returncode == 0:
            log.info("Closed app: %s (matched '%s')", label, name)
            return True, label

    # Last resort: substring match
    r = subprocess.run(["pkill", "-i", candidates[0]], capture_output=True)
    if r.returncode == 0:
        log.info("Closed app: %s (substring '%s')", label, candidates[0])
        return True, label

    log.warning("close: no running process found for '%s'", app_name)
    return False, label
