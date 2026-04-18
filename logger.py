"""Centralised logging for Vigil (console + rotating file)."""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "vigil"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = str(_DATA_DIR / "vigil.log")


def setup(name: str = "vigil") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:          # already initialised
        return logger
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    # Rotating file handler (1 MB, 3 backups)
    fh = RotatingFileHandler(_LOG_FILE, maxBytes=1_048_576, backupCount=3,
                             encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


log = setup()
