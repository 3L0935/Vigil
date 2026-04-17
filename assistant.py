"""llama-server assistant with function calling for notes, agenda and reminders."""

import json
from datetime import datetime
from logger import log
import config
import locales
import database as db
from llm_backend import LlamaServerBackend
from llm_manager import manager as _llm_manager

_backend = LlamaServerBackend(config.LLAMA_SERVER_URL, config.LLAMA_MODEL)

# ── Tool definitions ──────────────────────────────────────────────────────

_BASE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": "Save a free-text note. Use for generic notes, thoughts, reminders without a specific time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title":    {"type": "string", "description": "Short title for the note"},
                    "content":  {"type": "string", "description": "Full note content"},
                    "category": {"type": "string", "description": "Category: general, work, personal, idea",
                                 "default": "general"},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_list",
            "description": "Save a list (shopping list, todo list, packing list, etc).",
            "parameters": {
                "type": "object",
                "properties": {
                    "title":    {"type": "string", "description": "List title, e.g. 'Shopping', 'Todo'"},
                    "items":    {"type": "array", "items": {"type": "string"},
                                 "description": "List items"},
                    "category": {"type": "string", "description": "Category: shopping, todo, general",
                                 "default": "general"},
                },
                "required": ["title", "items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_list",
            "description": "Add items to an existing list note, found by title.",
            "parameters": {
                "type": "object",
                "properties": {
                    "list_title": {"type": "string", "description": "Title of the existing list"},
                    "items":      {"type": "array", "items": {"type": "string"},
                                   "description": "Items to add"},
                },
                "required": ["list_title", "items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_appointment",
            "description": "Create a calendar appointment with date and time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title":       {"type": "string", "description": "Appointment title"},
                    "datetime":    {"type": "string",
                                    "description": "ISO datetime, e.g. 2026-02-23T15:00"},
                    "description": {"type": "string", "description": "Optional details",
                                    "default": ""},
                },
                "required": ["title", "datetime"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Set a reminder that will trigger a notification at the specified time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message":   {"type": "string", "description": "What to remind about"},
                    "remind_at": {"type": "string",
                                  "description": "ISO datetime for the reminder, e.g. 2026-02-23T10:00"},
                },
                "required": ["message", "remind_at"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_notes",
            "description": "Show/search saved notes. Use when user asks to see their notes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Filter by category (optional)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_appointments",
            "description": "Show upcoming appointments/agenda.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_reminders",
            "description": "Show active (pending) reminders.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

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


def _get_tools() -> list[dict]:
    """Return tool list, adding optional tools based on config."""
    tools = list(_BASE_TOOLS)
    tools.append(_WEB_SEARCH_TOOL)
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
    """Execute a function call and return a localised confirmation string."""
    log.info("Assistant dispatch: %s(%s)", name, args)

    try:
        if name == "save_note":
            nid = db.save_note(
                content=args.get("content", ""),
                category=args.get("category", "general"),
                title=args.get("title", ""),
            )
            return locales.get("note_saved", nid=nid)

        elif name == "save_list":
            db.save_list(
                title=args.get("title", locales.get("default_list_title")),
                items=args.get("items", []),
                category=args.get("category", "general"),
            )
            return locales.get("list_saved",
                               title=args.get("title", ""),
                               count=len(args.get("items", [])))

        elif name == "add_to_list":
            existing = db.find_list_by_title(args.get("list_title", ""))
            if existing:
                db.add_to_list(existing["id"], args.get("items", []))
                return locales.get("added_to_list", title=existing["title"])
            return locales.get("list_not_found", title=args.get("list_title", ""))

        elif name == "create_appointment":
            db.create_appointment(
                title=args.get("title", ""),
                dt=args.get("datetime", ""),
                description=args.get("description", ""),
            )
            return locales.get("appointment_created",
                               title=args.get("title", ""),
                               dt=args.get("datetime", ""))

        elif name == "set_reminder":
            db.set_reminder(
                message=args.get("message", ""),
                remind_at=args.get("remind_at", ""),
            )
            return locales.get("reminder_set", dt=args.get("remind_at", ""))

        elif name == "list_notes":
            return "__show_notes__"

        elif name == "list_appointments":
            return "__show_appointments__"

        elif name == "list_reminders":
            return "__show_reminders__"

        elif name == "search_web":
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

        elif name == "search_obsidian_vault":
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
    """Process transcribed text through llama-server. Returns confirmation string.

    Special return values starting with '__show_' signal the caller
    to open the notes/agenda window.
    """
    _llm_manager.ensure_running()
    log.info("Assistant input: %r", text)

    data = _backend.chat(
        messages=[
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": text},
        ],
        tools=_get_tools(),
    )

    if data is None:
        return locales.get("not_understood")

    # Extract tool call from OpenAI-format response
    try:
        choices = data.get("choices", [])
        if not choices:
            return locales.get("not_understood")

        msg = choices[0].get("message", {})
        tool_calls = msg.get("tool_calls")

        if tool_calls:
            tc = tool_calls[0]
            fn_name = tc["function"]["name"]
            # llama-server returns arguments as a JSON string
            raw_args = tc["function"].get("arguments", "{}")
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    from json_repair import repair_json
                    args = repair_json(raw_args) or {}
            else:
                args = raw_args  # already a dict (shouldn't happen with llama-server)

            return _dispatch(fn_name, args)

        # No tool call: plain text response
        content = msg.get("content", "").strip()
        if content:
            log.info("LLM text response: %s", content)
            return content

    except (KeyError, IndexError, TypeError) as exc:
        log.error("Response parsing error: %s", exc)

    return locales.get("not_understood")
