"""llama-server assistant with function calling for web search and vault search."""

import json
from datetime import datetime
from pathlib import Path
from logger import log
import config
import locales
from llm_backend import LlamaServerBackend
from llm_manager import manager as _llm_manager

_backend = LlamaServerBackend(config.LLAMA_SERVER_URL, config.LLAMA_MODEL)

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
            "Open the Writher settings window. Use when the user asks to open settings, "
            "configure the app, change parameters, or says things like "
            "'ouvre les paramètres', 'open settings', 'show settings', 'apri le impostazioni'."
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


def _get_tools() -> list[dict]:
    tools = [_WEB_SEARCH_TOOL, _OPEN_SETTINGS_TOOL, _CLOSE_SETTINGS_TOOL, _LAUNCH_APP_TOOL, _CLOSE_APP_TOOL]
    if config.OBSIDIAN_VAULT_PATH:
        tools.append(_OBSIDIAN_TOOL)
    return tools


# ── System prompt ─────────────────────────────────────────────────────────

def _system_prompt() -> str:
    now = datetime.now()
    return locales.get(
        "system_prompt",
        now=now.strftime("%Y-%m-%d %H:%M"),
        weekday=now.strftime("%A"),
        lang_name=locales.get("lang_name"),
    )


# ── Function dispatcher ───────────────────────────────────────────────────

def _dispatch(name: str, args: dict) -> str:
    """Execute a search tool and return the raw results string."""
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
            ok, label = app_launcher.launch(args.get("app_name", ""))
            if ok:
                return locales.get("app_launched", name=label)
            return locales.get("app_not_found", name=label)

        elif name == "close_app":
            import app_launcher
            ok, label = app_launcher.close(args.get("app_name", ""))
            if ok:
                return locales.get("app_closed", name=label)
            return locales.get("app_close_failed", name=label)

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
    _llm_manager.ensure_running()
    log.info("Assistant input: %r", text)

    messages = [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": text},
    ]
    data = _backend.chat(messages=messages, tools=_get_tools())

    if data is None:
        return locales.get("not_understood")

    try:
        choices = data.get("choices", [])
        if not choices:
            return locales.get("not_understood")

        msg = choices[0].get("message", {})
        tool_calls = msg.get("tool_calls")

        if tool_calls:
            tc = tool_calls[0]
            fn_name = tc["function"]["name"]
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
                            return syn_content
                log.warning("Synthesis returned empty — falling back to raw search result")
                return raw_result

            return raw_result

        # No tool call: plain text response
        content = msg.get("content", "").strip()
        if content:
            log.info("LLM text response: %s", content)
            return content

    except (KeyError, IndexError, TypeError) as exc:
        log.error("Response parsing error: %s", exc)

    return locales.get("not_understood")
