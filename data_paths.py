"""Private application data paths shared by settings, logs and recovery."""
import os
from pathlib import Path

DATA_DIR = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'vigil'
DATA_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
DATA_DIR.chmod(0o700)


def private_file(path: Path) -> None:
    if path.exists():
        path.chmod(0o600)
