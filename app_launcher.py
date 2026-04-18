"""Launch installed applications via .desktop files."""

import os
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

# Detect system language (e.g. "fr" from "fr_FR.UTF-8")
_SYS_LANG = (
    os.environ.get("LANGUAGE", "").split(":")[0].split("_")[0]
    or os.environ.get("LANG", "").split("_")[0]
    or "en"
)


def _localized(cfg: dict, key: str) -> str:
    """Return cfg[key[lang]] if present, else cfg[key], else ''."""
    return cfg.get(f"{key}[{_SYS_LANG}]") or cfg.get(key, "")


def _parse_desktop(path: Path) -> dict | None:
    cfg = {}
    try:
        in_main = False
        for line in path.read_text(errors="replace").splitlines():
            s = line.strip()
            if s.startswith('['):
                in_main = (s == '[Desktop Entry]')
                continue
            if not in_main or s.startswith('#') or '=' not in s:
                continue
            k, _, v = s.partition('=')
            cfg[k.strip()] = v.strip()   # keep all keys incl. Name[fr] etc.
    except OSError:
        return None
    if cfg.get("Type") != "Application":
        return None
    if cfg.get("NoDisplay", "false").lower() == "true":
        return None
    if cfg.get("Terminal", "false").lower() == "true":
        return None
    name = _localized(cfg, "Name")
    exec_ = _FIELD_CODE_RE.sub('', cfg.get("Exec", "")).strip()
    if not name or not exec_:
        return None
    return {
        "name":     name,
        "exec":     exec_,
        "generic":  _localized(cfg, "GenericName"),
        "comment":  _localized(cfg, "Comment"),
        "keywords": _localized(cfg, "Keywords"),
    }


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
    """Return up to n app display names that fuzzy-match query.

    Searches name, GenericName, Comment, and Keywords so spoken descriptions
    like "paramètres système" can match even when the display name differs.
    """
    import difflib
    q = query.lower().strip()
    apps = _list_apps()

    # Build (search_text → display_name) pairs; multiple per app
    pairs: list[tuple[str, str]] = []
    seen_search: set[str] = set()
    for app in apps:
        display = app["name"]
        candidates_fields = [
            app["name"],
            app.get("generic", ""),
            app.get("comment", ""),
        ] + [kw for kw in app.get("keywords", "").split(";") if kw.strip()]
        for field in candidates_fields:
            s = field.lower().strip()
            if s and s not in seen_search:
                seen_search.add(s)
                pairs.append((s, display))

    search_strings = [p[0] for p in pairs]
    raw = difflib.get_close_matches(q, search_strings, n=n * 3, cutoff=0.55)

    # Map back to display names, deduplicate, preserve relevance order
    seen_display: set[str] = set()
    result: list[str] = []
    str_to_display = {s: d for s, d in pairs}
    for m in raw:
        display = str_to_display.get(m)
        if display and display not in seen_display:
            seen_display.add(display)
            result.append(display)
            if len(result) >= n:
                break
    return result


def _find_app(query: str) -> dict | None:
    q = query.lower().strip()
    apps = _list_apps()
    for app in apps:
        if app["name"].lower() == q:
            return app
    for app in apps:
        if app.get("generic", "").lower() == q:
            return app
    for app in apps:
        if app["name"].lower().startswith(q):
            return app
    for app in apps:
        if q in app["name"].lower():
            return app
    for app in apps:
        if q in app.get("generic", "").lower():
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
