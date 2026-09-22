"""Pure Python validation and safe asset download helpers."""

import os
from ipaddress import ip_address
from pathlib import Path
import tempfile
from urllib.parse import urlsplit
import urllib.request


def url_is_valid(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        return (parsed.scheme in ("http", "https") and bool(parsed.hostname)
                and parsed.username is None and parsed.password is None
                and parsed.port != -1)
    except ValueError:
        return False


def is_loopback_url(url: str) -> bool:
    if not url_is_valid(url):
        return False
    host = urlsplit(url).hostname.lower()
    if host == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def download_voice(name: str) -> None:
    """Install a Piper voice only after both files have downloaded."""
    lang_full, rest = name.split("-", 1)
    speaker, quality = rest.rsplit("-", 1)
    lang = lang_full.split("_")[0].lower()
    base = ("https://huggingface.co/rhasspy/piper-voices/resolve/main/"
            f"{lang}/{lang_full}/{speaker}/{quality}/{name}")
    dest_dir = Path.home() / ".local/share/vigil/tts/piper"
    dest_dir.mkdir(parents=True, exist_ok=True)
    pending = []
    try:
        for ext in (".onnx.json", ".onnx"):
            dest = dest_dir / (name + ext)
            if dest.is_file() and dest.stat().st_size:
                continue
            with tempfile.NamedTemporaryFile(dir=dest_dir, prefix=name + ".", delete=False) as tmp:
                partial = Path(tmp.name)
            pending.append((partial, dest))
            urllib.request.urlretrieve(base + ext, partial)
            if partial.stat().st_size == 0:
                raise ValueError("Empty voice download")
        for partial, dest in pending:
            os.replace(partial, dest)
    finally:
        for partial, _ in pending:
            partial.unlink(missing_ok=True)
