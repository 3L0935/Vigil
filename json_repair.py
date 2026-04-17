"""
JSON repair heuristics for malformed tool call arguments from local LLMs.

Local models (especially <14B) frequently produce broken JSON:
  - Trailing commas: {"a": 1,}
  - Missing closing braces/brackets
  - Single quotes instead of double quotes
  - Unquoted keys: {key: "value"}
  - Trailing text after valid JSON: {"a": 1} some extra text
  - Truncated strings (model ran out of tokens mid-value)

This module attempts lightweight repairs before falling back to an error.
It does NOT use eval() or any unsafe parsing — only regex and string ops.
"""

from __future__ import annotations

import json
import re


def repair_json(raw: str) -> dict | None:
    """Attempt to repair malformed JSON and return a parsed dict.

    Returns None if repair fails. Never raises.
    """
    if not raw or not raw.strip():
        return None

    text = raw.strip()

    # Try parsing as-is first (fast path)
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Apply repair strategies in order of likelihood
    for strategy in (_strip_trailing_text, _fix_quotes, _fix_trailing_commas, _close_brackets, _extract_json_block):
        try:
            fixed = strategy(text)
            if fixed and fixed != text:
                result = json.loads(fixed)
                if isinstance(result, dict):
                    return result
        except (json.JSONDecodeError, ValueError):
            continue

    # Last resort: try combining multiple fixes
    try:
        fixed = text
        fixed = _fix_quotes(fixed)
        fixed = _fix_trailing_commas(fixed)
        fixed = _close_brackets(fixed)
        result = json.loads(fixed)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    return None


def _strip_trailing_text(s: str) -> str:
    """Remove text after the last closing brace of a JSON object."""
    # Find the outermost {} block
    depth = 0
    end = -1
    for i, c in enumerate(s):
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                end = i
                break
    if end > 0:
        return s[:end + 1]
    return s


def _fix_quotes(s: str) -> str:
    """Replace single quotes with double quotes (common Python-dict-as-JSON error)."""
    # Only fix if no double quotes are present (avoid breaking valid JSON)
    if '"' in s:
        # Fix unquoted keys: {key: "value"} → {"key": "value"}
        fixed = re.sub(r'(?<=[{,])\s*(\w+)\s*:', r' "\1":', s)
        return fixed
    return s.replace("'", '"')


def _fix_trailing_commas(s: str) -> str:
    """Remove trailing commas before } or ]."""
    return re.sub(r',\s*([}\]])', r'\1', s)


def _close_brackets(s: str) -> str:
    """Close unclosed braces and brackets (truncated output)."""
    opens = 0
    open_sq = 0
    in_string = False
    escape = False

    for c in s:
        if escape:
            escape = False
            continue
        if c == '\\':
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == '{':
            opens += 1
        elif c == '}':
            opens -= 1
        elif c == '[':
            open_sq += 1
        elif c == ']':
            open_sq -= 1

    # Close unclosed strings first (truncated mid-string)
    if in_string:
        s += '"'

    # Remove trailing comma before closing
    s = re.sub(r',\s*$', '', s)

    # Close brackets
    s += ']' * max(0, open_sq)
    s += '}' * max(0, opens)

    return s


def _extract_json_block(s: str) -> str:
    """Extract a JSON object from surrounding text/markdown."""
    # Try to find ```json ... ``` blocks
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', s, re.DOTALL)
    if match:
        return match.group(1)

    # Try to find the first { ... } in the text
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', s)
    if match:
        return match.group(0)

    return s
