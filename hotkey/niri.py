"""niri adapter — managed block nested inside binds { } in config.kdl.

niri's config uses KDL syntax; hotkeys live in a single `binds { }` block.
Unlike Hyprland/Sway, the managed fence has to live INSIDE that block
(not at the top level) and use KDL comments (//) rather than bash-style (#).

niri reloads automatically via inotify; no reload command needed.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from hotkey.base import HotkeyAdapter
from logger import log

_FENCE_START = "// >>> vigil managed (do not edit) >>>"
_FENCE_END = "// <<< vigil managed <<<"


def _to_niri_combo(combo: str) -> str:
    """Ctrl+Alt+W → Ctrl+Alt+W (niri accepts combos mostly as-is)."""
    parts = [p.strip() for p in combo.split("+")]
    tokens: list[str] = []
    for part in parts:
        upper = part.upper()
        if upper == "CTRL":
            tokens.append("Ctrl")
        elif upper == "SHIFT":
            tokens.append("Shift")
        elif upper in ("ALT", "ALTGR"):
            tokens.append("Alt")
        elif upper in ("META", "SUPER", "WIN"):
            tokens.append("Super")
        elif len(part) == 1:
            tokens.append(part.upper())
        else:
            tokens.append(part)
    return "+".join(tokens)


def _find_binds_block(content: str) -> tuple[int, int] | None:
    """Return (open_brace_end, close_brace_start) for `binds { … }`, or None.

    Naive brace-depth scan that ignores braces inside strings is Good Enough
    — niri configs don't put `{` or `}` inside string literals in practice.
    """
    m = re.search(r"\bbinds\s*\{", content)
    if not m:
        return None
    start = m.end()
    depth = 1
    i = start
    while i < len(content) and depth > 0:
        c = content[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return start, i
        i += 1
    return None


def _read_managed_entries(block_body: str) -> dict[str, str]:
    """Parse the fenced vigil block inside a binds { ... } body."""
    m = re.search(
        re.escape(_FENCE_START) + r"\n(.*?)\n\s*" + re.escape(_FENCE_END),
        block_body, re.DOTALL,
    )
    if not m:
        return {}
    entries: dict[str, str] = {}
    for line in m.group(1).splitlines():
        m2 = re.search(r"// id=(\S+)\s*$", line)
        if m2:
            entries[m2.group(1)] = line
    return entries


def _render_fenced_block(entries: dict[str, str], indent: str = "    ") -> str:
    body = "\n".join(entries[k] for k in sorted(entries))
    return f"{indent}{_FENCE_START}\n{body}\n{indent}{_FENCE_END}"


class NiriAdapter(HotkeyAdapter):
    name = "niri"

    def _config_path(self) -> Path:
        xdg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        return Path(xdg) / "niri" / "config.kdl"

    def is_available(self) -> bool:
        return bool(os.environ.get("NIRI_SOCKET")) or self._config_path().exists()

    def register(self, action_id: str, combo: str,
                 command: list[str] | None = None) -> bool:
        if command is None:
            command = ["vigil-trigger", action_id]
        combo_niri = _to_niri_combo(combo)
        cmd_tokens = " ".join(f'"{c}"' for c in command)
        line = f"    {combo_niri} {{ spawn {cmd_tokens}; }}  // id={action_id}"
        return self._update_block(lambda entries: {**entries, action_id: line})

    def unregister(self, action_id: str) -> bool:
        def remove(entries: dict[str, str]) -> dict[str, str]:
            out = dict(entries)
            out.pop(action_id, None)
            return out
        return self._update_block(remove)

    def list_registered(self) -> list[str]:
        path = self._config_path()
        if not path.exists():
            return []
        content = path.read_text()
        span = _find_binds_block(content)
        if span is None:
            return []
        body = content[span[0]:span[1]]
        return list(_read_managed_entries(body).keys())

    # ── internals ────────────────────────────────────────────────────────

    def _update_block(self, mutate) -> bool:
        path = self._config_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            content = path.read_text() if path.exists() else ""

            span = _find_binds_block(content)
            if span is None:
                # no binds { } block yet — append one.
                content = content.rstrip() + "\n\nbinds {\n}\n"
                span = _find_binds_block(content)
                if span is None:
                    log.warning("niri: failed to create binds block")
                    return False

            body_start, body_end = span
            before = content[:body_start]
            body = content[body_start:body_end]
            after = content[body_end:]

            entries = _read_managed_entries(body)
            entries = mutate(entries)

            # strip any prior fence from body
            body_without = re.sub(
                re.escape(_FENCE_START) + r"\n.*?\n\s*" + re.escape(_FENCE_END)
                + r"\s*\n?",
                "",
                body,
                flags=re.DOTALL,
            )

            if entries:
                new_block = _render_fenced_block(entries) + "\n"
                # Ensure the binds body ends with a newline before we insert.
                if not body_without.endswith("\n"):
                    body_without += "\n"
                new_body = body_without + new_block
            else:
                new_body = body_without

            path.write_text(before + new_body + after)
            return True
        except Exception as exc:
            log.warning("niri adapter: update failed: %s", exc)
            return False
