"""Obsidian vault search for Vigil.

Scans .md files in the vault directory, matches query tokens,
and returns ranked results with title, excerpt, tags and file path.
"""

import re
from pathlib import Path


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter. Returns (meta_dict, body_text)."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("\n---", 3)
    if end == -1:
        return {}, content
    meta: dict = {}
    for line in content[3:end].splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, content[end + 4:]


def search_vault(
    query: str,
    vault_path: str,
    max_results: int = 5,
) -> list[dict]:
    """Search .md files in vault_path for notes matching query.

    Returns up to max_results dicts: {title, path, excerpt, tags, score}.
    Score = number of distinct query tokens found in the note body.
    """
    if not query or not vault_path or not Path(vault_path).is_dir():
        return []

    tokens = [t.lower() for t in query.split() if len(t) > 1]
    if not tokens:
        return []

    results = []
    for md_file in Path(vault_path).rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        meta, body = _parse_frontmatter(content)
        body_lower = body.lower()

        score = sum(1 for t in tokens if t in body_lower)
        if score == 0:
            continue

        # Excerpt: 200 chars around first token match
        first_token = tokens[0]
        idx = body_lower.find(first_token)
        start = max(0, idx - 60)
        excerpt = body[start:start + 200].strip().replace("\n", " ")

        # Collect tags from frontmatter and inline #hashtags
        fm_tags_raw = meta.get("tags", "")
        fm_tags = re.findall(r"[\w/-]+", fm_tags_raw) if fm_tags_raw else []
        inline_tags = re.findall(r"#([\w/-]+)", body)
        tags = list(dict.fromkeys(fm_tags + inline_tags))  # dedupe, preserve order

        results.append({
            "title": meta.get("title") or md_file.stem,
            "path": str(md_file),
            "excerpt": excerpt,
            "tags": tags,
            "score": score,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_results]
