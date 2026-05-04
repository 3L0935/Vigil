"""llama-server assistant with function calling for web search and vault search."""

import json
import subprocess
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
            "Open Vigil's OWN settings/configuration panel. "
            "Use ONLY when the user explicitly wants to configure Vigil itself: "
            "'ouvre les paramètres de Vigil', 'open Vigil settings', 'show settings', "
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
            "Close the Vigil settings window if it is currently open. Use when the user asks "
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
            "Launch an INSTALLED desktop application by name (a program that lives "
            "on this computer, not a website). "
            "Examples: 'lance Kitty', 'ouvre Firefox', 'open Thunderbird', "
            "'lancia Gimp', 'démarre VLC', 'start Steam'. "
            "Do NOT use for websites like YouTube, Netflix, GitHub, Gmail → use "
            "open_url instead. "
            "Do NOT use for opening a specific file or folder → use open_path instead. "
            "If you are not certain of the exact name, try your best guess — if not "
            "found, the system will suggest matching installed apps so you can retry."
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

_OPEN_URL_TOOL = {
    "type": "function",
    "function": {
        "name": "open_url",
        "description": (
            "Open a WEBSITE in the user's default browser. Use when the user wants "
            "a website / online service rather than a desktop application. "
            "Examples (voice): 'lance youtube' → open_url('youtube'), "
            "'ouvre github' → open_url('github'), 'open netflix' → "
            "open_url('netflix'), 'va sur reddit' → open_url('reddit'), "
            "'open my gmail' → open_url('gmail'). "
            "Pass the SITE KEYWORD as the user spoke it. Known keywords include: "
            "youtube, netflix, twitch, spotify, soundcloud, github, gitlab, gmail, "
            "outlook, twitter, x, instagram, reddit, tiktok, amazon, chatgpt, "
            "claude, gemini, wikipedia, drive, maps, discord, whatsapp, telegram, "
            "and ~30 others. "
            "Do NOT use for desktop apps installed on the system (Firefox, VLC, "
            "Kitty, Steam, Gimp, …) → use launch_app instead. "
            "Do NOT use for local folders → use open_folder."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Site keyword the user spoke (e.g. 'youtube', 'github', 'gmail').",
                },
            },
            "required": ["target"],
        },
    },
}

_OPEN_FOLDER_TOOL = {
    "type": "function",
    "function": {
        "name": "open_folder",
        "description": (
            "Open one of the user's standard folders in the file manager. "
            "Examples (voice): 'ouvre mon dossier téléchargements' → "
            "open_folder('downloads'), 'open my documents' → "
            "open_folder('documents'), 'apri le immagini' → "
            "open_folder('pictures'), 'ouvre ma musique' → open_folder('music'). "
            "Pass a SHORT FOLDER NAME the user mentioned. Recognised names "
            "(any language): downloads/téléchargements/scaricati, "
            "documents/documenti, pictures/images/immagini, videos/vidéos/video, "
            "music/musique/musica, desktop/bureau/scrivania, "
            "templates/modèles/modelli, public/publique/pubblica. "
            "Do NOT use to launch an app → use launch_app. "
            "Do NOT use for websites → use open_url. "
            "Do NOT invent paths or use slashes — pass a folder name only."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Folder keyword the user spoke (e.g. 'downloads', 'documents', 'musique').",
                },
            },
            "required": ["name"],
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

_ASK_USER_CHOICE_TOOL = {
    "type": "function",
    "function": {
        "name": "ask_user_choice",
        "description": (
            "Ask the user to pick between 2-4 similar installed apps when the request is "
            "genuinely ambiguous. The user replies with a number (1, 2, 3, ...) and the "
            "chosen app is then launched or closed. Use this ONLY after a launch_app retry "
            "when several candidates fit the user's intent equally well. "
            "Do NOT use for single-best-match cases — call launch_app directly instead."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "2-4 app names to present to the user, copied exactly from the installed-apps list.",
                },
                "action": {
                    "type": "string",
                    "enum": ["launch", "close"],
                    "description": "What to do with the chosen app.",
                },
            },
            "required": ["options", "action"],
        },
    },
}


def _get_tools() -> list[dict]:
    tools = [_WEB_SEARCH_TOOL, _OPEN_SETTINGS_TOOL, _CLOSE_SETTINGS_TOOL,
             _LAUNCH_APP_TOOL, _CLOSE_APP_TOOL, _OPEN_URL_TOOL, _OPEN_FOLDER_TOOL,
             _CLEAR_CONTEXT_TOOL, _ASK_USER_CHOICE_TOOL]
    if config.OBSIDIAN_VAULT_PATH:
        tools.append(_OBSIDIAN_TOOL)
    return tools


# ── System prompt ─────────────────────────────────────────────────────────

def _system_prompt() -> str:
    now = datetime.now()
    return locales.get(
        "system_prompt",
        name=getattr(config, "ASSISTANT_NAME", "Vigil"),
        now=now.strftime("%Y-%m-%d %H:%M"),
        weekday=now.strftime("%A"),
        lang_name=locales.get("lang_name"),
    )


# ── Function dispatcher ───────────────────────────────────────────────────

_RETRY_STOPWORDS = frozenset({
    # action verbs / glue (fr/en/it) — ignored when mining keywords from user_text
    "lance", "lances", "lancer", "ouvre", "ouvres", "ouvrir", "démarre", "démarrer",
    "ferme", "fermer", "quitte", "quitter", "arrête", "arrêter", "peux", "peux-tu",
    "tu", "me", "moi", "stp", "svp",
    "launch", "open", "start", "run", "close", "quit", "stop", "please", "could", "can",
    "you", "me", "my",
    "apri", "avvia", "chiudi", "lancia", "ferma", "puoi",
    "le", "la", "les", "un", "une", "des", "du", "de", "ton", "ta", "tes", "mon", "ma",
    "mes", "ce", "cet", "cette", "ces",
    "the", "a", "an", "your", "my", "this", "that",
    "il", "lo", "gli", "i", "le", "uno", "una",
})


def _extract_intent_tokens(text: str) -> list[str]:
    """Strip stopwords from user_text so the remaining tokens are the ones
    that actually identify the app (e.g. 'musique', 'navigateur')."""
    if not text:
        return []
    import re
    words = re.findall(r"[\w'’-]+", text.lower())
    return [w for w in words if w and w not in _RETRY_STOPWORDS and len(w) > 2]


def _build_launch_retry_context(app_name: str, user_text: str) -> str:
    """Build retry feedback for the LLM after a launch_app failure.

    Mines intent tokens from user_text (minus stopwords) and fuzzy-matches
    each against installed apps so short significant words like 'musique'
    surface the right candidates instead of being drowned by the full
    mistranscribed sentence. Language follows config.LANGUAGE so the model's
    plain-text fallback ends up in the user's language.
    """
    import app_launcher
    seen: set[str] = set()
    cands: list[str] = []
    # 1. Intent tokens from user's raw utterance (most semantic)
    for token in _extract_intent_tokens(user_text):
        for c in app_launcher.find_candidates(token, n=4, cutoff=0.5):
            if c not in seen:
                seen.add(c)
                cands.append(c)
    # 2. Fallback on the failed name itself (handles near-typo cases)
    for c in app_launcher.find_candidates(app_name, n=5, cutoff=0.3):
        if c not in seen:
            seen.add(c)
            cands.append(c)
    cands = cands[:8]
    if not cands:
        return locales.get("retry_launch_ctx_empty", name=app_name)
    meta = {a["name"]: a for a in app_launcher.list_all_apps()}
    lines = []
    for c in cands:
        m = meta.get(c, {})
        generic = m.get("generic", "")
        kws = [k.strip() for k in m.get("keywords", "").split(";") if k.strip()][:5]
        parts = [f"- {c}"]
        if generic:
            parts.append(f"({generic})")
        if kws:
            parts.append(f"[{', '.join(kws)}]")
        lines.append(" ".join(parts))
    return locales.get("retry_launch_ctx", name=app_name, list="\n".join(lines))


def _dispatch(name: str, args: dict, user_text: str = "") -> tuple[str, str | None]:
    """Execute a tool and return (user_facing_text, retry_context_or_None).

    If retry_context is non-None, the caller (process) should re-query the LLM
    with this as a tool result so it can correct a failed launch_app call.
    """
    global _waiting_for_reply, _pending_candidates, _pending_action
    log.info("Assistant dispatch: %s(%s)", name, args)

    try:
        if name == "search_web":
            from ddgs import DDGS
            query = args.get("query", "")
            max_results = min(int(args.get("max_results", 5)), 10)
            results = list(DDGS().text(query, max_results=max_results))
            if not results:
                return (locales.get("web_no_results", query=query), None)
            lines = []
            for r in results:
                title = r.get("title", "")
                body  = r.get("body", "")
                href  = r.get("href", "")
                lines.append(f"**{title}**\n{body}\n{href}")
            return ("\n\n".join(lines), None)

        elif name == "open_settings":
            cb = _action_callbacks.get("open_settings")
            if cb:
                cb()
            return (locales.get("settings_opened"), None)

        elif name == "close_settings":
            cb = _action_callbacks.get("close_settings")
            if cb:
                cb()
            return (locales.get("settings_closed"), None)

        elif name == "search_obsidian_vault":
            if not config.OBSIDIAN_VAULT_PATH or not Path(config.OBSIDIAN_VAULT_PATH).is_dir():
                return (locales.get("vault_not_configured"), None)
            from obsidian import search_vault
            results = search_vault(
                query=args.get("query", ""),
                vault_path=config.OBSIDIAN_VAULT_PATH,
                max_results=args.get("max_results", 5),
            )
            if not results:
                return (locales.get("vault_no_results", query=args.get("query", "")), None)
            lines = []
            for r in results:
                lines.append(f"**{r['title']}**\n{r['excerpt']}")
            return ("\n\n".join(lines), None)

        elif name == "launch_app":
            import app_launcher
            app_name = args.get("app_name", "")
            ok, label = app_launcher.launch(app_name)
            if ok:
                return (locales.get("app_launched", name=label), None)
            # Exact match failed — try fuzzy
            candidates = app_launcher.find_candidates(app_name)
            if len(candidates) == 1:
                ok2, label2 = app_launcher.launch(candidates[0])
                text = locales.get("app_launched", name=label2) if ok2 else locales.get("app_not_found", name=label2)
                return (text, None)
            if len(candidates) > 1:
                with _context_lock:
                    _waiting_for_reply  = True
                    _pending_candidates = candidates
                    _pending_action     = "launch"
                lines = "\n".join(f"{i + 1}: {c}" for i, c in enumerate(candidates))
                return (locales.get("app_candidates", list=lines), None)
            # Zero candidates — ask the LLM to retry with installed-app hints,
            # and if the requested name matches a known web shortcut, push it
            # towards open_url instead of guessing more apps.
            retry_ctx = _build_launch_retry_context(app_name, user_text)
            import url_shortcuts
            if url_shortcuts.is_known(app_name):
                retry_ctx = (
                    retry_ctx + "\n\n"
                    + locales.get("retry_launch_url_hint", name=app_name)
                )
            return (locales.get("app_not_found", name=app_name), retry_ctx)

        elif name == "close_app":
            import app_launcher
            app_name = args.get("app_name", "")
            ok, label = app_launcher.close(app_name)
            if ok:
                return (locales.get("app_closed", name=label), None)
            # Exact match failed — try fuzzy
            candidates = app_launcher.find_candidates(app_name)
            if len(candidates) == 1:
                ok2, label2 = app_launcher.close(candidates[0])
                text = locales.get("app_closed", name=label2) if ok2 else locales.get("app_close_failed", name=label2)
                return (text, None)
            if len(candidates) > 1:
                with _context_lock:
                    _waiting_for_reply  = True
                    _pending_candidates = candidates
                    _pending_action     = "close"
                lines = "\n".join(f"{i + 1}: {c}" for i, c in enumerate(candidates))
                return (locales.get("app_candidates", list=lines), None)
            return (locales.get("app_close_failed", name=app_name), None)

        elif name == "ask_user_choice":
            options = args.get("options") or []
            action  = args.get("action", "launch")
            if action not in ("launch", "close"):
                action = "launch"
            opts = [str(o) for o in options if o][:4]
            if not opts:
                return (locales.get("app_not_found", name=""), None)
            with _context_lock:
                _waiting_for_reply  = True
                _pending_candidates = opts
                _pending_action     = action
            lines = "\n".join(f"{i + 1}: {c}" for i, c in enumerate(opts))
            return (locales.get("app_candidates", list=lines), None)

        elif name == "open_url":
            import url_shortcuts
            target = (args.get("target") or "").strip()
            url = url_shortcuts.resolve(target)
            if not url:
                return (locales.get("url_invalid", target=target), None)
            try:
                subprocess.Popen(
                    ["xdg-open", url],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            except Exception as exc:
                return (locales.get("url_invalid", target=target), None)
            return (locales.get("url_opened", url=url), None)

        elif name == "open_folder":
            import folders
            folder_name = (args.get("name") or "").strip()
            path = folders.resolve(folder_name)
            if path is None:
                return (locales.get("folder_unknown", name=folder_name), None)
            if not path.exists():
                return (locales.get("folder_missing", path=str(path)), None)
            try:
                subprocess.Popen(
                    ["xdg-open", str(path)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            except Exception:
                return (locales.get("folder_missing", path=str(path)), None)
            return (locales.get("folder_opened", path=str(path)), None)

        elif name == "clear_context":
            reset_context()
            return (locales.get("context_cleared"), None)

        else:
            return (locales.get("unknown_command", name=name), None)

    except Exception as exc:
        log.error("Dispatch error: %s", exc)
        return (locales.get("error", detail=str(exc)), None)


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

            raw_result, retry_ctx = _dispatch(fn_name, args, user_text=text)

            # Launch retry: LLM hit a not-found — give it candidate apps and
            # let it try again once. No further retry from that second call.
            if retry_ctx is not None:
                log.info("launch_app retry: feeding %d chars of context back to LLM", len(retry_ctx))
                tool_call_id = tc.get("id", "tc_0")
                retry_messages = messages + [
                    {"role": "assistant", "tool_calls": [tc]},
                    {"role": "tool", "tool_call_id": tool_call_id, "content": retry_ctx},
                ]
                retry_data = _backend.chat(messages=retry_messages, tools=_get_tools())
                if retry_data:
                    try:
                        retry_msg = retry_data.get("choices", [{}])[0].get("message", {})
                        retry_tcs = retry_msg.get("tool_calls")
                        if retry_tcs:
                            rtc = retry_tcs[0]
                            retry_fn = rtc["function"]["name"]
                            retry_raw = rtc["function"].get("arguments", "{}")
                            if isinstance(retry_raw, str):
                                try:
                                    retry_args = json.loads(retry_raw)
                                except json.JSONDecodeError:
                                    from json_repair import repair_json
                                    retry_args = repair_json(retry_raw) or {}
                            else:
                                retry_args = retry_raw
                            # Execute once, ignore any further retry_ctx to avoid loops
                            retry_text, _ = _dispatch(retry_fn, retry_args, user_text=text)
                            if retry_text:
                                raw_result = retry_text
                        else:
                            retry_content = retry_msg.get("content", "").strip()
                            if retry_content:
                                log.info("Retry text response: %s", retry_content[:120])
                                raw_result = retry_content
                    except (KeyError, IndexError, TypeError) as exc:
                        log.error("Retry parsing error: %s", exc)
                else:
                    log.warning("Retry returned None — using original not-found message")

            # Search tools: feed results back to LLM for a concise synthesis
            elif fn_name in _SEARCH_TOOLS:
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
