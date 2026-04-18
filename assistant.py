"""llama-server assistant with function calling for web search and vault search."""

import json
import threading
import time as _time
from datetime import datetime
from pathlib import Path
from logger import log
import config
import locales
from llm_backend import LlamaServerBackend
from llm_manager import manager as _llm_manager

_backend = LlamaServerBackend(config.LLAMA_SERVER_URL, config.LLAMA_MODEL)

# ── Multi-turn conversation context ───────────────────────────────────────

_CONTEXT_TIMEOUT  = 30.0       # seconds of inactivity before auto-reset
_context_lock     = threading.Lock()
_conversation_history: list[dict] = []
_last_interaction: float = 0.0
_waiting_for_reply: bool = False
_pending_candidates: list[str] = []
_pending_action: str = ""      # "launch" or "close"

_WORD_TO_NUM: dict[str, int] = {
    "one": 1, "un": 1, "uno": 1,
    "two": 2, "deux": 2, "due": 2,
    "three": 3, "trois": 3, "tre": 3,
    "four": 4, "quatre": 4, "quattro": 4,
}


def reset_context() -> None:
    global _conversation_history, _last_interaction, _waiting_for_reply
    global _pending_candidates, _pending_action
    with _context_lock:
        _conversation_history = []
        _last_interaction     = 0.0
        _waiting_for_reply    = False
        _pending_candidates   = []
        _pending_action       = ""


def is_waiting() -> bool:
    with _context_lock:
        return _waiting_for_reply


def context_level() -> int:
    """Number of completed turns (each turn = 1 user + 1 assistant message)."""
    with _context_lock:
        return len(_conversation_history) // 2


def _parse_number(text: str) -> int | None:
    t = text.strip().lower()
    try:
        return int(t)
    except ValueError:
        pass
    for word, num in _WORD_TO_NUM.items():
        if word in t.split():
            return num
    return None


# ── Action callbacks (registered by main.py) ──────────────────────────────

_action_callbacks: dict = {}


def register_action(name: str, fn) -> None:
    _action_callbacks[name] = fn


# ── Tool definitions ──────────────────────────────────────────────────────

_SEARCH_TOOLS = {"search_web", "search_obsidian_vault"}

_WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": (
            "Search the web via DuckDuckGo. Use when the user asks about current events, "
            "facts, prices, news, or anything that requires up-to-date information from the internet. "
            "Examples: 'cherche sur internet', 'search the web', 'look up', 'what is X', 'latest news about X'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query":       {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "description": "Max results (1-10)", "default": 5},
            },
            "required": ["query"],
        },
    },
}

_OBSIDIAN_TOOL = {
    "type": "function",
    "function": {
        "name": "search_obsidian_vault",
        "description": (
            "Search the user's Obsidian vault for notes matching a query. "
            "Use when the user says 'check dans ma vault', 'cherche dans mes notes', "
            "'look in my vault', 'search my notes', or similar."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query":       {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "description": "Max notes to return", "default": 5},
            },
            "required": ["query"],
        },
    },
}


_OPEN_SETTINGS_TOOL = {
    "type": "function",
    "function": {
        "name": "open_settings",
        "description": (
            "Open Writher's OWN settings/configuration panel. "
            "Use ONLY when the user explicitly wants to configure Writher itself: "
            "'ouvre les paramètres de Writher', 'open Writher settings', 'show settings', "
            "'apri le impostazioni'. "
            "Do NOT use for OS settings, KDE settings, system settings, or any other "
            "application's settings — use launch_app for those instead."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}

_CLOSE_SETTINGS_TOOL = {
    "type": "function",
    "function": {
        "name": "close_settings",
        "description": (
            "Close the Writher settings window if it is currently open. Use when the user asks "
            "to close or hide the settings: 'ferme les paramètres', 'close settings', "
            "'hide settings', 'chiudi le impostazioni'."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}

_LAUNCH_APP_TOOL = {
    "type": "function",
    "function": {
        "name": "launch_app",
        "description": (
            "Launch an installed application by name. Use when the user asks to open or launch "
            "a program: 'lance Kitty', 'ouvre Firefox', 'open Thunderbird', 'lancia Gimp', "
            "'démarre VLC', 'start Steam', etc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Application name to launch"},
            },
            "required": ["app_name"],
        },
    },
}

_CLOSE_APP_TOOL = {
    "type": "function",
    "function": {
        "name": "close_app",
        "description": (
            "Close a running application by name. Use when the user asks to close, quit, "
            "kill, or stop a program: 'ferme Firefox', 'close Kitty', 'quitte VLC', "
            "'chiudi Gimp', 'arrête Zen Browser', 'kill Steam', etc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Application name to close"},
            },
            "required": ["app_name"],
        },
    },
}

_CLEAR_CONTEXT_TOOL = {
    "type": "function",
    "function": {
        "name": "clear_context",
        "description": (
            "Clear the conversation history and reset context. "
            "Use when the user asks to clear, reset, or restart the conversation: "
            "'nettoie la conv', 'clear context', 'reset context', 'effacer la conversation', "
            "'pulisci la conversazione', 'start over', 'repart a zero', 'recommence'."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}


def _get_tools() -> list[dict]:
    tools = [_WEB_SEARCH_TOOL, _OPEN_SETTINGS_TOOL, _CLOSE_SETTINGS_TOOL,
             _LAUNCH_APP_TOOL, _CLOSE_APP_TOOL, _CLEAR_CONTEXT_TOOL]
    if config.OBSIDIAN_VAULT_PATH:
        tools.append(_OBSIDIAN_TOOL)
    return tools


# ── System prompt ─────────────────────────────────────────────────────────

def _system_prompt() -> str:
    now = datetime.now()
    return locales.get(
        "system_prompt",
        name=getattr(config, "ASSISTANT_NAME", "WritHer"),
        now=now.strftime("%Y-%m-%d %H:%M"),
        weekday=now.strftime("%A"),
        lang_name=locales.get("lang_name"),
    )


# ── Function dispatcher ───────────────────────────────────────────────────

def _dispatch(name: str, args: dict) -> str:
    """Execute a search tool and return the raw results string."""
    global _waiting_for_reply, _pending_candidates, _pending_action
    log.info("Assistant dispatch: %s(%s)", name, args)

    try:
        if name == "search_web":
            from ddgs import DDGS
            query = args.get("query", "")
            max_results = min(int(args.get("max_results", 5)), 10)
            results = list(DDGS().text(query, max_results=max_results))
            if not results:
                return locales.get("web_no_results", query=query)
            lines = []
            for r in results:
                title = r.get("title", "")
                body  = r.get("body", "")
                href  = r.get("href", "")
                lines.append(f"**{title}**\n{body}\n{href}")
            return "\n\n".join(lines)

        elif name == "open_settings":
            cb = _action_callbacks.get("open_settings")
            if cb:
                cb()
            return locales.get("settings_opened")

        elif name == "close_settings":
            cb = _action_callbacks.get("close_settings")
            if cb:
                cb()
            return locales.get("settings_closed")

        elif name == "search_obsidian_vault":
            if not config.OBSIDIAN_VAULT_PATH or not Path(config.OBSIDIAN_VAULT_PATH).is_dir():
                return locales.get("vault_not_configured")
            from obsidian import search_vault
            results = search_vault(
                query=args.get("query", ""),
                vault_path=config.OBSIDIAN_VAULT_PATH,
                max_results=args.get("max_results", 5),
            )
            if not results:
                return locales.get("vault_no_results", query=args.get("query", ""))
            lines = []
            for r in results:
                lines.append(f"**{r['title']}**\n{r['excerpt']}")
            return "\n\n".join(lines)

        elif name == "launch_app":
            import app_launcher
            app_name = args.get("app_name", "")
            ok, label = app_launcher.launch(app_name)
            if ok:
                return locales.get("app_launched", name=label)
            # Exact match failed — try fuzzy
            candidates = app_launcher.find_candidates(app_name)
            if len(candidates) == 1:
                ok2, label2 = app_launcher.launch(candidates[0])
                return locales.get("app_launched", name=label2) if ok2 else locales.get("app_not_found", name=label2)
            if len(candidates) > 1:
                with _context_lock:
                    _waiting_for_reply  = True
                    _pending_candidates = candidates
                    _pending_action     = "launch"
                lines = "\n".join(f"{i + 1}: {c}" for i, c in enumerate(candidates))
                return locales.get("app_candidates", list=lines)
            return locales.get("app_not_found", name=app_name)

        elif name == "close_app":
            import app_launcher
            app_name = args.get("app_name", "")
            ok, label = app_launcher.close(app_name)
            if ok:
                return locales.get("app_closed", name=label)
            # Exact match failed — try fuzzy
            candidates = app_launcher.find_candidates(app_name)
            if len(candidates) == 1:
                ok2, label2 = app_launcher.close(candidates[0])
                return locales.get("app_closed", name=label2) if ok2 else locales.get("app_close_failed", name=label2)
            if len(candidates) > 1:
                with _context_lock:
                    _waiting_for_reply  = True
                    _pending_candidates = candidates
                    _pending_action     = "close"
                lines = "\n".join(f"{i + 1}: {c}" for i, c in enumerate(candidates))
                return locales.get("app_candidates", list=lines)
            return locales.get("app_close_failed", name=app_name)

        elif name == "clear_context":
            reset_context()
            return locales.get("context_cleared")

        else:
            return locales.get("unknown_command", name=name)

    except Exception as exc:
        log.error("Dispatch error: %s", exc)
        return locales.get("error", detail=str(exc))


# ── Public API ────────────────────────────────────────────────────────────

def ping_llama_server() -> bool:
    """Quick connectivity check. Returns True if llama-server is reachable."""
    return _backend.ping()


def reload_backend():
    global _backend
    _backend = LlamaServerBackend(config.LLAMA_SERVER_URL, config.LLAMA_MODEL)
    log.info("LLM backend reloaded (URL: %s)", config.LLAMA_SERVER_URL)


def process(text: str) -> str:
    """Process transcribed text through llama-server. Returns answer string."""
    global _conversation_history, _last_interaction, _waiting_for_reply
    global _pending_candidates, _pending_action

    _llm_manager.ensure_running()
    log.info("Assistant input: %r", text)

    # Snapshot mutable state under the lock
    with _context_lock:
        waiting        = _waiting_for_reply
        candidates     = list(_pending_candidates)
        action         = _pending_action
        history        = list(_conversation_history)
        last_time      = _last_interaction

    # Auto-reset on timeout
    now = _time.monotonic()
    if history and (now - last_time) > _CONTEXT_TIMEOUT:
        log.info("Context timeout — resetting conversation")
        reset_context()
        with _context_lock:
            history  = []
            waiting  = False

    # Resolve pending numbered reply
    if waiting:
        n = _parse_number(text)
        if n is not None and 1 <= n <= len(candidates):
            app_name = candidates[n - 1]
            log.info("Resolving candidate %d: %s (action=%s)", n, app_name, action)
            with _context_lock:
                _waiting_for_reply  = False
                _pending_candidates = []
                _pending_action     = ""
            import app_launcher
            if action == "launch":
                ok, label = app_launcher.launch(app_name)
                result = locales.get("app_launched", name=label) if ok else locales.get("app_not_found", name=label)
            else:
                ok, label = app_launcher.close(app_name)
                result = locales.get("app_closed", name=label) if ok else locales.get("app_close_failed", name=label)
            with _context_lock:
                _conversation_history.append({"role": "user",      "content": text})
                _conversation_history.append({"role": "assistant",  "content": result})
                if len(_conversation_history) > 20:
                    _conversation_history = _conversation_history[-20:]
                _last_interaction = _time.monotonic()
            return result
        else:
            # Not a valid number — drop waiting state and process normally
            with _context_lock:
                _waiting_for_reply  = False
                _pending_candidates = []
                _pending_action     = ""

    # Normal LLM flow (with history for multi-turn)
    messages = [{"role": "system", "content": _system_prompt()}] + history + [
        {"role": "user", "content": text},
    ]
    data = _backend.chat(messages=messages, tools=_get_tools())

    if data is None:
        return locales.get("not_understood")

    result = locales.get("not_understood")
    _context_cleared_flag = False
    try:
        choices = data.get("choices", [])
        if not choices:
            return locales.get("not_understood")

        msg = choices[0].get("message", {})
        tool_calls = msg.get("tool_calls")

        if tool_calls:
            tc = tool_calls[0]
            fn_name = tc["function"]["name"]
            _context_cleared_flag = (fn_name == "clear_context")
            raw_args = tc["function"].get("arguments", "{}")
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    from json_repair import repair_json
                    args = repair_json(raw_args) or {}
            else:
                args = raw_args

            raw_result = _dispatch(fn_name, args)

            # Search tools: feed results back to LLM for a concise synthesis
            if fn_name in _SEARCH_TOOLS:
                tool_call_id = tc.get("id", "tc_0")
                synthesis_messages = messages + [
                    {"role": "assistant", "tool_calls": [tc]},
                    {"role": "tool", "tool_call_id": tool_call_id, "content": raw_result},
                ]
                syn_data = _backend.chat(messages=synthesis_messages, tools=None)
                if syn_data:
                    syn_choices = syn_data.get("choices", [])
                    if syn_choices:
                        syn_content = (syn_choices[0]
                                       .get("message", {})
                                       .get("content", "")
                                       .strip())
                        if syn_content:
                            log.info("Synthesis: %s", syn_content[:120])
                            raw_result = syn_content
                        else:
                            log.warning("Synthesis empty — using raw result")
                else:
                    log.warning("Synthesis returned None — using raw result")

            result = raw_result

        else:
            # No tool call: plain text response
            content = msg.get("content", "").strip()
            if content:
                log.info("LLM text response: %s", content)
                result = content

    except (KeyError, IndexError, TypeError) as exc:
        log.error("Response parsing error: %s", exc)
        return locales.get("not_understood")

    # Append this turn to history (skip if clear_context was called)
    with _context_lock:
        if not _context_cleared_flag:
            _conversation_history.append({"role": "user",      "content": text})
            _conversation_history.append({"role": "assistant",  "content": result})
            if len(_conversation_history) > 20:
                _conversation_history = _conversation_history[-20:]
        _last_interaction = _time.monotonic()

    return result
