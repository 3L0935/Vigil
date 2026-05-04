"""Recursive file search for the search_files voice tool.

Resolves a folder keyword (via folders.py), walks it recursively with caps
(depth, file count, time), tokenises the user's query with month-name
expansion (fr/en/it ↔ digits), scores each file by tokens matched in any
path component, returns 2 buckets: strict (all tokens) and similar
(>=1 token) for fallback suggestions.

Voice-only design — query is the natural-language phrase the user spoke,
not a regex or glob pattern.
"""

from __future__ import annotations
import os
import re
import time
import unicodedata
from datetime import datetime
from pathlib import Path

import folders

# ── Limits ───────────────────────────────────────────────────────────────────

_MAX_DEPTH      = 4
_MAX_FILES      = 5000
_MAX_TIME_S     = 3.0
_RESULTS_CAP    = 10

# Skip these directory names anywhere in the walk — common build/cache/vcs noise
# that bloats results without value to a voice user.
_SKIP_DIRS = frozenset({
    ".git", ".hg", ".svn",
    "node_modules", "__pycache__", ".venv", "venv", ".env",
    "dist", "build", "target", ".next", ".cache",
    ".idea", ".vscode",
})

# Stopwords to drop from the user's query before tokenising. fr/en/it.
_STOPWORDS = frozenset({
    "le", "la", "les", "un", "une", "des", "du", "de", "d", "l",
    "the", "a", "an", "of", "in", "for", "to", "is", "exists", "exist",
    "il", "lo", "gli", "i", "uno", "una", "del", "della",
    "mon", "ma", "mes", "ton", "ta", "tes", "ce", "cette", "ces",
    "my", "your", "this", "that", "these", "those",
    "cherche", "trouve", "regarde", "look", "search", "find",
    "cerca", "trova", "guarda",
    "si", "if", "se",
    "et", "and", "ou", "or", "o",
    "fichier", "file", "documento",
    "dans", "in", "nel",
})


# ── Month name ↔ digit expansion ─────────────────────────────────────────────

# canonical key (lowercased, accent-stripped) → list of all aliases (incl. digits)
_MONTH_ALIASES: dict[str, list[str]] = {
    "01": ["01", "1", "janvier", "jan", "january", "gennaio"],
    "02": ["02", "2", "fevrier", "fev", "february", "feb", "febbraio"],
    "03": ["03", "3", "mars", "mar", "march", "marzo"],
    "04": ["04", "4", "avril", "avr", "april", "apr", "aprile"],
    "05": ["05", "5", "mai", "may", "maggio"],
    "06": ["06", "6", "juin", "jun", "june", "giugno"],
    "07": ["07", "7", "juillet", "juil", "jul", "july", "luglio"],
    "08": ["08", "8", "aout", "aug", "august", "agosto"],
    "09": ["09", "9", "septembre", "sep", "sept", "september", "settembre"],
    "10": ["10", "octobre", "oct", "october", "ottobre"],
    "11": ["11", "novembre", "nov", "november"],
    "12": ["12", "decembre", "dec", "december", "dicembre"],
}

# Reverse index: any alias → set of all aliases (so matching is bidirectional).
# E.g. "mars" → {"03", "3", "mars", "mar", "march", "marzo"}.
_TOKEN_EXPANSIONS: dict[str, frozenset[str]] = {}
for _aliases in _MONTH_ALIASES.values():
    _set = frozenset(_aliases)
    for _a in _aliases:
        _TOKEN_EXPANSIONS[_a] = _set


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def _normalise(s: str) -> str:
    """Lowercase, strip accents, keep alphanumerics + dots/hyphens."""
    return _strip_accents(s.strip().lower())


def _tokenise(text: str) -> list[str]:
    """Split text into significant tokens. Drops stopwords and 1-char fragments."""
    if not text:
        return []
    norm = _normalise(text)
    raw = re.findall(r"[a-z0-9]+", norm)
    return [t for t in raw if t not in _STOPWORDS and len(t) > 1]


def _expand_token(token: str) -> frozenset[str]:
    """Return the token plus any known synonyms (e.g. 'mars' ↔ '03')."""
    syns = _TOKEN_EXPANSIONS.get(token)
    if syns:
        return syns
    return frozenset({token})


def _path_tokens(path: Path, root: Path) -> set[str]:
    """All tokens drawn from path components below root (folders + filename
    stem, no extension). Used as the searchable text for one file."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    parts: list[str] = []
    for p in rel.parts[:-1]:           # parent directories
        parts.append(p)
    parts.append(path.stem)            # filename without extension
    seen: set[str] = set()
    for part in parts:
        seen.update(_tokenise(part))
    return seen


def _token_matches(file_tokens: set[str], syns: frozenset[str]) -> bool:
    """A query synonym matches if EITHER:
       - it equals a file token exactly (digit synonyms like '03' need this), OR
       - it shares a 4+ char substring with a file token (handles plurals,
         minor spelling variations: 'facture' ↔ 'factures', 'doc' ↔ 'docs').
    Substring is symmetric — query token in file token, or file token in
    query token — so 'facture' matches 'factures' and vice versa."""
    for s in syns:
        if s in file_tokens:
            return True
        if len(s) >= 4:
            for ft in file_tokens:
                if len(ft) >= 4 and (s in ft or ft in s):
                    return True
    return False


def _score_file(path: Path, root: Path,
                expanded_query: list[frozenset[str]]) -> tuple[int, list[str]]:
    """Returns (matched_count, matched_token_canonical_names).

    A query token is considered matched if ANY of its synonyms appears in the
    file's path tokens. This handles "mars" matching "03" inside the basename
    AND "facture" matching the parent dir "factures" via substring rule.
    """
    file_tokens = _path_tokens(path, root)
    matched = 0
    matched_names: list[str] = []
    for syns in expanded_query:
        if _token_matches(file_tokens, syns):
            matched += 1
            alpha = next((s for s in syns if not s.isdigit()), None)
            matched_names.append(alpha or next(iter(syns)))
    return matched, matched_names


def _walk(root: Path, deadline: float) -> list[Path]:
    """Bounded recursive walk. Honours depth cap, file cap, time deadline,
    and skips common build/vcs noise directories."""
    out: list[Path] = []
    if not root.is_dir():
        return out
    root_depth = len(root.parts)
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        if time.monotonic() > deadline:
            break
        depth = len(Path(dirpath).parts) - root_depth
        if depth >= _MAX_DEPTH:
            dirnames[:] = []
            continue
        # Filter out skip-dirs and dotted dirs (in-place to prune walk)
        dirnames[:] = [d for d in dirnames
                       if d not in _SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            if fname.startswith("."):
                continue
            out.append(Path(dirpath) / fname)
            if len(out) >= _MAX_FILES:
                return out
    return out


def _format_mtime(p: Path) -> str:
    try:
        ts = p.stat().st_mtime
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    except OSError:
        return ""


def _file_size_kb(p: Path) -> int:
    try:
        return max(1, p.stat().st_size // 1024)
    except OSError:
        return 0


def search(folder_keyword: str, query: str,
           include_size: bool = False, include_date: bool = False) -> dict:
    """Search a standard folder for files matching the query.

    Returns:
        {
            "folder_resolved": "/home/elo/Documents",  # for display/error msg
            "found":   [ {name, path, [mtime], [size_kb]}, ... ],   # all-tokens match
            "similar": [ {name, path, matched, [mtime], [size_kb]}, ... ],  # >=1 match
            "scanned": <int>,                          # files actually walked
        }

        If folder_keyword can't be resolved → {"folder_resolved": None, ...}
        If folder doesn't exist → "found"/"similar" empty, scanned=0

        mtime/size_kb are omitted from each item unless the corresponding
        include_* flag is True (keeps the LLM context tight when not needed).
    """
    root = folders.resolve(folder_keyword)
    out = {
        "folder_resolved": str(root) if root else None,
        "found":   [],
        "similar": [],
        "scanned": 0,
    }
    if root is None:
        return out
    if not root.is_dir():
        return out

    tokens = _tokenise(query)
    if not tokens:
        # Query is all stopwords — no point walking.
        return out

    expanded = [_expand_token(t) for t in tokens]

    deadline = time.monotonic() + _MAX_TIME_S
    files = _walk(root, deadline)
    out["scanned"] = len(files)

    strict: list[tuple[Path, list[str]]] = []
    loose:  list[tuple[Path, int, list[str]]] = []
    for f in files:
        matched, names = _score_file(f, root, expanded)
        if matched == 0:
            continue
        if matched == len(expanded):
            strict.append((f, names))
        else:
            loose.append((f, matched, names))

    # Sort: strict by mtime desc; loose by matched count desc then mtime desc.
    strict.sort(key=lambda x: x[0].stat().st_mtime if x[0].exists() else 0,
                reverse=True)
    loose.sort(key=lambda x: (x[1], x[0].stat().st_mtime if x[0].exists() else 0),
               reverse=True)

    def _mk(p: Path, matched: list[str] | None = None) -> dict:
        item = {
            "name": p.name,
            "path": str(p),
        }
        if matched is not None:
            item["matched"] = matched
        if include_date:
            item["mtime"] = _format_mtime(p)
        if include_size:
            item["size_kb"] = _file_size_kb(p)
        return item

    out["found"]   = [_mk(p) for p, _ in strict[:_RESULTS_CAP]]
    out["similar"] = [_mk(p, names) for p, _m, names in loose[:_RESULTS_CAP // 2]]
    return out
