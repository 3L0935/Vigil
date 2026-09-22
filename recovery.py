"""Bounded plaintext recovery for failed pastes; never write inside the repo."""
from datetime import datetime, timedelta
import threading

import database as db
from data_paths import DATA_DIR, private_file

RECOVERY_FILE = DATA_DIR / 'recovery_notes.txt'
_lock = threading.Lock()
_MAX_BYTES = 1_048_576


def retention_days() -> int:
    try:
        return max(0, min(30, int(db.get_setting('recovery_days', '7'))))
    except ValueError:
        return 7


def _retained() -> str:
    if not RECOVERY_FILE.exists() or retention_days() == 0:
        return ''
    cutoff = datetime.now() - timedelta(days=retention_days())
    # Bound memory even if the file has been modified outside Vigil.
    with RECOVERY_FILE.open('rb') as stream:
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(max(0, size - _MAX_BYTES))
        if size > _MAX_BYTES:
            stream.readline()
        lines = stream.read().decode('utf-8', errors='replace').splitlines()
    result = []
    for line in lines:
        try:
            date = datetime.strptime(line[1:20], '%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue
        if date >= cutoff:
            result.append(line)
    return '\n'.join(result) + ('\n' if result else '')


def _write(content: str) -> None:
    if not content:
        RECOVERY_FILE.unlink(missing_ok=True)
        return
    lines = content.splitlines(keepends=True)
    size = len(content.encode('utf-8'))
    while lines and size > _MAX_BYTES:
        size -= len(lines.pop(0).encode('utf-8'))
    RECOVERY_FILE.write_text(''.join(lines), encoding='utf-8')
    private_file(RECOVERY_FILE)


def prune() -> None:
    with _lock:
        _write(_retained())


def save(text: str) -> bool:
    with _lock:
        if retention_days() == 0:
            _write('')
            return False
        # One timestamped record per line, including multi-paragraph dictations.
        stamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        content = _retained() + ''.join(f'[{stamp}] {line}\n' for line in text.splitlines())
        _write(content)
        return RECOVERY_FILE.exists()


def purge() -> None:
    with _lock:
        RECOVERY_FILE.unlink(missing_ok=True)
