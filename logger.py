"""Centralised logging for Vigil (console + rotating file)."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from data_paths import DATA_DIR, private_file

_LOG_FILE = str(DATA_DIR / "vigil.log")
_content_enabled = False


def configure_content_logging(enabled: bool) -> None:
    global _content_enabled
    _content_enabled = enabled


def log_content(message: str, *args) -> None:
    if _content_enabled:
        log.info(message, *args)


def purge_logs() -> None:
    """Truncate the active log without leaving a handler on an unlinked inode."""
    for handler in log.handlers:
        if isinstance(handler, RotatingFileHandler):
            handler.acquire()
            try:
                handler.flush()
                if handler.stream:
                    handler.stream.close()
                Path(handler.baseFilename).write_text("")
                handler.stream = handler._open()
                for i in range(1, handler.backupCount + 1):
                    Path(f"{handler.baseFilename}.{i}").unlink(missing_ok=True)
            finally:
                handler.release()


class _PrivateRotatingHandler(RotatingFileHandler):
    def _open(self):
        stream = super()._open()
        private_file(Path(self.baseFilename))
        return stream


def setup(name: str = "vigil") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:          # already initialised
        return logger
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    # Rotating file handler (1 MB, 3 backups)
    fh = _PrivateRotatingHandler(_LOG_FILE, maxBytes=1_048_576, backupCount=3,
                             encoding="utf-8")
    private_file(Path(_LOG_FILE))
    for path in DATA_DIR.glob("vigil.log.*"):
        private_file(path)
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
