"""Standard folder resolver for the open_folder voice tool.

Maps spoken folder names (any of fr/en/it) to XDG user dirs. Resolves the
actual filesystem path via xdg-user-dir at call time so the user's locale
configuration is respected (e.g. ~/Téléchargements vs ~/Downloads).

Voice-only tool — no path-style input is accepted; the LLM passes the
keyword the user spoke and we look it up here.
"""

from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path

# Spoken keyword (lowercased, accent-stripped) → XDG user-dir code
_ALIASES: dict[str, str] = {
    # Downloads
    "downloads": "DOWNLOAD",
    "download": "DOWNLOAD",
    "telechargements": "DOWNLOAD",
    "téléchargements": "DOWNLOAD",
    "telechargement": "DOWNLOAD",
    "scaricati": "DOWNLOAD",

    # Documents
    "documents": "DOCUMENTS",
    "document": "DOCUMENTS",
    "documenti": "DOCUMENTS",

    # Pictures
    "pictures": "PICTURES",
    "picture": "PICTURES",
    "images": "PICTURES",
    "image": "PICTURES",
    "photos": "PICTURES",
    "photo": "PICTURES",
    "immagini": "PICTURES",
    "immagine": "PICTURES",

    # Videos
    "videos": "VIDEOS",
    "video": "VIDEOS",
    "vidéos": "VIDEOS",
    "vidéo": "VIDEOS",
    "videoteca": "VIDEOS",

    # Music
    "music": "MUSIC",
    "musique": "MUSIC",
    "musica": "MUSIC",

    # Desktop
    "desktop": "DESKTOP",
    "bureau": "DESKTOP",
    "scrivania": "DESKTOP",

    # Templates
    "templates": "TEMPLATES",
    "template": "TEMPLATES",
    "modeles": "TEMPLATES",
    "modèles": "TEMPLATES",
    "modelli": "TEMPLATES",

    # Public share
    "public": "PUBLICSHARE",
    "publique": "PUBLICSHARE",
    "pubblica": "PUBLICSHARE",
}

# Fallback paths if xdg-user-dir is missing or returns $HOME (= unset)
_FALLBACK: dict[str, str] = {
    "DOWNLOAD":    "~/Downloads",
    "DOCUMENTS":   "~/Documents",
    "PICTURES":    "~/Pictures",
    "VIDEOS":      "~/Videos",
    "MUSIC":       "~/Music",
    "DESKTOP":     "~/Desktop",
    "TEMPLATES":   "~/Templates",
    "PUBLICSHARE": "~/Public",
}


def _normalise(name: str) -> str:
    return name.strip().lower()


def resolve(name: str) -> Path | None:
    """Return the filesystem Path for a spoken folder keyword, or None.

    Resolution: alias lookup → xdg-user-dir → fallback to ~/StdName.
    Path is returned even if the directory doesn't exist on disk — caller
    decides whether to create it or surface an error.
    """
    if not name:
        return None
    code = _ALIASES.get(_normalise(name))
    if not code:
        return None
    home = Path.home()
    if shutil.which("xdg-user-dir"):
        try:
            out = subprocess.run(
                ["xdg-user-dir", code],
                capture_output=True, text=True, timeout=2,
            )
            cand = out.stdout.strip()
            # xdg-user-dir returns $HOME when the dir is unconfigured — we treat
            # that as "fall back to the conventional name" rather than dumping
            # the user into their home directory.
            if cand and Path(cand) != home:
                return Path(cand)
        except Exception:
            pass
    return Path(os.path.expanduser(_FALLBACK[code]))
