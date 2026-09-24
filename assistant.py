"""llama-server assistant with function calling for web search and vault search."""

import json
import re
import subprocess
import threading
import time as _time
from pathlib import Path
from logger import log, log_content
import privacy
import config
import locales
from llm_backend import LlamaServerBackend
from llm_manager import manager as _llm_manager
import app_launcher
import url_shortcuts
import folders
import file_search
from assistant_tools import (InvalidToolCall, PendingChoice, ToolResult,
                             message_result, validate_call)
from assistant_prompts import system_prompt

def _get_backend():
    """Create the appropriate backend based on DB provider settings.

    Reads the DB directly (like llm_manager does) so config is not the source
    of truth for the LLM stack. Previously this read config.LLAMA_MODEL /
    config.LLM_PROVIDER, which were constants never populated from the DB,
    so the model name sent to llama-server was a dead placeholder.
    """
    import database as db
    provider = db.get_setting("llm_provider", "llama_cpp")
    if provider == "ollama_local":
        return LlamaServerBackend(
            db.get_setting("ollama_local_url", "http://localhost:11434"),
            db.get_setting("ollama_model", ""),
            provider="ollama_local",
            use_model_profile=db.get_setting("llm_profile", "compat") == "model",
        )
    if provider == "ollama_cloud":
        return LlamaServerBackend(
            db.get_setting("ollama_cloud_url", "https://ollama.com"),
            db.get_setting("ollama_model", ""),
            db.get_setting("ollama_api_key", ""),
            provider="ollama_cloud",
            use_model_profile=db.get_setting("llm_profile", "compat") == "model",
        )
    return LlamaServerBackend(
        db.get_setting("llama_server_url", "http://localhost:8081"),
        db.get_setting("llama_model", ""),
        use_model_profile=db.get_setting("llm_profile", "compat") == "model",
    )

_history_policy = None
_history_has_local_data = False

# ── Multi-turn conversation context ───────────────────────────────────────

_CONTEXT_TIMEOUT  = 30.0       # seconds of inactivity before auto-reset
_context_lock     = threading.Lock()
_conversation_history: list[dict] = []
_last_interaction: float = 0.0
_pending_choice: PendingChoice | None = None

# True when the most recent process() result came from the synthesis pass
# (raw tool result re-fed to the LLM for a spoken-language paraphrase).
# Lets main.py decide whether to TTS while in waiting state — search_files
# results are paraphrased and worth speaking, app_candidates lists are raw
# and would sound bad.
_last_was_synthesised: bool = False
_last_spoken_result: str = ""
_last_source_refs: list[str] = []


def was_last_synthesised() -> bool:
    return _last_was_synthesised


def spoken_reply(result: str) -> str:
    return _last_spoken_result or result

_WORD_TO_NUM: dict[str, int] = {
    # cardinals
    "one": 1, "un": 1, "uno": 1,
    "two": 2, "deux": 2, "due": 2,
    "three": 3, "trois": 3, "tre": 3,
    "four": 4, "quatre": 4, "quattro": 4,
    "five": 5, "cinq": 5, "cinque": 5,
    # ordinals (user often replies "la première" / "the first")
    "first":  1, "premier": 1, "premiere": 1, "première": 1, "primo": 1, "prima": 1,
    "second": 2, "deuxieme": 2, "deuxième": 2, "seconde": 2, "secondo": 2, "seconda": 2,
    "third":  3, "troisieme": 3, "troisième": 3, "terzo": 3, "terza": 3,
    "fourth": 4, "quatrieme": 4, "quatrième": 4, "quarto": 4, "quarta": 4,
    "fifth":  5, "cinquieme": 5, "cinquième": 5, "quinto": 5, "quinta": 5,
}

# Phonetic Whisper-FR mistranscriptions of the digit "1" — interjections that
# the user may not actually have said but that come out when they say "1".
# Ambiguous (could just mean "huh?"), so only accepted as a number reply when
# the whole transcript is short (≤ 2 words). Avoids treating "hein attends
# c'est quoi" as choice #1.
_PHONETIC_ONE = frozenset({"hein", "han", "ein", "in"})

# Hardcoded keywords that trigger a context reset without going through the
# LLM. Faster than a tool call, frees one tool slot for the small model, and
# the regex match is unambiguous on these phrasings (fr/en/it). Match is on
# the full transcript lowercased+stripped — substring match so things like
# "non, nettoie la conv" still work.
_CLEAR_CONTEXT_PATTERNS = (
    "nettoie la conv", "nettoie la conversation", "efface la conv",
    "efface la conversation", "repart à zéro", "repart a zero",
    "recommence", "remet à zéro", "remet a zero",
    "clear context", "reset context", "start over", "start fresh",
    "pulisci la conversazione", "ricomincia", "azzera",
)


def _is_clear_context_request(text: str) -> bool:
    t = text.strip().lower().rstrip(".!? ")
    return t in _CLEAR_CONTEXT_PATTERNS


_NEGATED_ACTION = re.compile(
    r"^(?:n['’](?:ouvre|lance|démarre|ferme)|ne\s+(?:ouvre|lance|démarre|ferme))"
    r"\s+pas\s+\S|^(?:do not|don't|never)\s+(?:open|launch|start|close)\s+\S"
    r"|^non\s+(?:apri|aprire|lanciare|chiudere)\s+\S",
    re.IGNORECASE,
)
_TWO_TARGETS = re.compile(
    r"^(?:ouvre|lance|open|launch|start|apri|avvia)\s+"
    r"[\w.-]+\s+(?:et|and|e)\s+[\w.-]+[.!?]?$",
    re.IGNORECASE,
)


def _is_negated_action(text: str) -> bool:
    return bool(_NEGATED_ACTION.match(text.strip()))


def _has_two_explicit_targets(text: str) -> bool:
    return bool(_TWO_TARGETS.fullmatch(text.strip()))


def reset_context() -> None:
    global _conversation_history, _last_interaction, _pending_choice
    global _history_has_local_data
    with _context_lock:
        _history_has_local_data = False
        _conversation_history = []
        _last_interaction     = 0.0
        _pending_choice       = None


def is_waiting() -> bool:
    with _context_lock:
        return _pending_choice is not None


def context_level() -> int:
    """Number of completed turns (each turn = 1 user + 1 assistant message)."""
    with _context_lock:
        return len(_conversation_history) // 2


def _parse_number(text: str) -> int | None:
    """Tolerant number parser for voice replies. Handles:
       - bare digits with trailing punctuation: "1", "1.", "2 !"
       - cardinals fr/en/it: "un", "deux", "two", "due"
       - ordinals fr/en/it: "première", "second", "troisième", "primo"
       - phonetic Whisper-FR misreads of "1" (hein, han, ein, in) when the
         transcript is short — Whisper sometimes hears "1" as the interjection.
    Returns None if nothing parseable is found."""
    t = text.strip().lower().rstrip(".,!?;: ")
    t = re.sub(r"^(?:ouvre|ouvrir|open|apri)\s+(?:(?:la|le|the|il)\s+)?", "", t)
    if not re.fullmatch(r"(?:\d+|[\wÀ-ÿ]+|(?:la|le|the|il)\s+[\wÀ-ÿ]+)", t):
        return None
    try:
        return int(t)
    except ValueError:
        pass
    words = re.findall(r"\w+", t, flags=re.UNICODE)
    short = len(words) <= 2
    for w in words:
        if w in _WORD_TO_NUM:
            return _WORD_TO_NUM[w]
        if w in _PHONETIC_ONE and short:
            return 1
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
            "Search the web via DuckDuckGo. Use for facts, news, prices, or real-time "
            "information the model does not know internally. "
            "Example: \"cherche sur internet\" or \"what is X\" >> calls with query parameter."
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
            "Search the user's Obsidian vault (.md notes) for content matching a query. "
            "Use when the user asks about information in their notes or saved documents. "
            "Example: \"cherche dans ma vault\" or \"look in my notes\" >> search the vault."
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
            "Open Vigil's own settings/preferences window. Use ONLY when the user asks to "
            "configure Vigil itself. If the user says \"parametres\" without naming a target, "
            "assume Vigil's settings. "
            "Example: \"ouvre les paramètres de Vigil\" >> open_settings()."
            "Do NOT use for OS/system settings -- use app_action('System Settings', 'launch')."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}

_CLOSE_SETTINGS_TOOL = {
    "type": "function",
    "function": {
        "name": "close_settings",
        "description": (
            "Close Vigil's own settings window."
            "Example: \"ferme les paramètres\" >> close_settings()."
            "Do NOT use for OS/system settings -- use app_action('System Settings', 'close')."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}

_APP_ACTION_TOOL = {
    "type": "function",
    "function": {
        "name": "app_action",
        "description": (
            "Launch or close an INSTALLED desktop application (not a website). "
            "The 'action' parameter specifies 'launch' or 'close'. If the exact name "
            "is uncertain, give your best guess -- the system will suggest matches. "
            "Examples: \"lance Firefox\" >> app_action('Firefox', 'launch'), "
            "            \"ferme VLC\" >> app_action('VLC', 'close')."
            "Do NOT use for: websites (use open_url), local folders (use open_folder)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Installed application name.",
                },
                "action": {
                    "type": "string",
                    "enum": ["launch", "close"],
                    "description": "What to do: 'launch' to start, 'close' to stop a running instance.",
                },
            },
            "required": ["name", "action"],
        },
    },
}

_OPEN_URL_TOOL = {
    "type": "function",
    "function": {
        "name": "open_url",
        "description": (
            "Open a website in the default browser. Pass the site keyword as the user "
            "spoke it (e.g. 'youtube', 'github', 'gmail'). ~50 sites are recognized. "
            "Example: \"ouvre YouTube\" >> open_url('youtube')."
            "Do NOT use for: desktop apps (use app_action), folders (use open_folder)."
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
            "Open one of the user's standard folders (Documents, Downloads, Pictures, "
            "Videos, Music, Desktop, Templates, Public) in the file manager. "
            "Pass a short folder keyword the user mentioned (in any language). "
            "Example: \"ouvre mes téléchargements\" >> open_folder('downloads')."
            "Do NOT use for: apps (use app_action), websites (use open_url)."
            "Do NOT invent paths or use slashes."
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

_SEARCH_FILES_TOOL = {
    "type": "function",
    "function": {
        "name": "search_files",
        "description": (
            "Search standard folders for a specific file by name or keywords. "
            "After the results, the user can reply with a number to open the chosen file. "
            "Set include_date=true for time-sensitive files (invoices, screenshots). "
            "Set include_size=true ONLY if the user explicitly asks for file size. "
            "Example: \"cherche facture de mars dans downloads\" >> "
            "        search_files(folder='downloads', query='facture mars')."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "folder": {
                    "type": "string",
                    "description": "Standard folder keyword (downloads, documents, pictures, music, videos, desktop, ...).",
                },
                "query": {
                    "type": "string",
                    "description": "What to look for, in natural language (e.g. 'facture mars', 'photo Paris', 'CV').",
                },
                "include_date": {
                    "type": "boolean",
                    "description": "Set true when the file type makes the modification date useful (invoices, dated documents). Default false.",
                    "default": False,
                },
                "include_size": {
                    "type": "boolean",
                    "description": "Set true ONLY when the user explicitly asked for the file size. Default false.",
                    "default": False,
                },
            },
            "required": ["folder", "query"],
        },
    },
}

_LOCAL_TOOLS = {"search_obsidian_vault", "search_files", "open_folder", "app_action"}
_WEB_TOOLS = {"search_web", "open_url"}


def _get_tools() -> list[dict]:
    tools = [_WEB_SEARCH_TOOL, _OPEN_SETTINGS_TOOL, _CLOSE_SETTINGS_TOOL,
             _APP_ACTION_TOOL, _OPEN_URL_TOOL, _OPEN_FOLDER_TOOL,
             _SEARCH_FILES_TOOL]
    if config.OBSIDIAN_VAULT_PATH:
        tools.append(_OBSIDIAN_TOOL)
    endpoint = _get_backend()._url
    return [tool for tool in tools
            if (tool['function']['name'] not in _WEB_TOOLS or privacy.web_allowed())
            and (tool['function']['name'] not in _LOCAL_TOOLS
                 or privacy.local_tools_allowed(endpoint))]


# ── System prompt ─────────────────────────────────────────────────────────

def _system_prompt() -> str:
    return system_prompt(getattr(config, "ASSISTANT_NAME", "Vigil"),
                         locales.get("lang_name"))


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


def _dispatch(name: str, args: dict, user_text: str = "") -> ToolResult:
    """Execute one validated action; presentation is handled by the caller."""
    global _pending_choice
    global _last_source_refs
    log.info("Assistant dispatch: %s", name)
    log_content("Assistant arguments: %s", args)
    if name in _WEB_TOOLS:
        privacy.require_web()
    if name in _LOCAL_TOOLS:
        privacy.check_endpoint(_get_backend()._url, local_data=True)

    try:
        if name == "search_web":
            from ddgs import DDGS
            query = args.get("query", "")
            max_results = min(int(args.get("max_results", 5)), 10)
            results = list(DDGS().text(query, max_results=max_results))
            if not results:
                return message_result("not_found", "web_no_results", query=query)
            bounded = []
            for r in results:
                title = str(r.get("title", ""))[:160]
                body  = str(r.get("body", ""))[:240]
                href  = str(r.get("href", ""))[:512]
                bounded.append({"title": title, "body": body, "href": href})
                if href:
                    _last_source_refs.append(href)
            return ToolResult("ok", {"kind": "web_results", "results": bounded})

        elif name == "open_settings":
            cb = _action_callbacks.get("open_settings")
            if not cb:
                return message_result("error", "assistant_error")
            cb()
            return message_result("ok", "settings_opened")

        elif name == "close_settings":
            cb = _action_callbacks.get("close_settings")
            if not cb:
                return message_result("error", "assistant_error")
            cb()
            return message_result("ok", "settings_closed")

        elif name == "search_obsidian_vault":
            if not config.OBSIDIAN_VAULT_PATH or not Path(config.OBSIDIAN_VAULT_PATH).is_dir():
                return message_result("not_found", "vault_not_configured")
            from obsidian import search_vault
            results = search_vault(
                query=args.get("query", ""),
                vault_path=config.OBSIDIAN_VAULT_PATH,
                max_results=args.get("max_results", 5),
            )
            if not results:
                return message_result("not_found", "vault_no_results", query=args["query"])
            bounded = []
            for r in results:
                title = str(r["title"])[:160]
                filename = Path(r["path"]).name
                bounded.append({"title": title, "excerpt": str(r["excerpt"])[:200],
                                "filename": filename})
                _last_source_refs.append(f"{title} — {filename}")
            return ToolResult("ok", {"kind": "vault_results", "results": bounded})

        elif name == "app_action":
            app_name = (args.get("name") or "").strip()
            action   = args.get("action")
            if action not in ("launch", "close"):
                return message_result("error", "not_understood")
            if action == "launch" and url_shortcuts.is_known(app_name):
                installed = {app["name"].casefold() for app in app_launcher.list_all_apps()}
                if app_name.casefold() not in installed:
                    if privacy.web_allowed():
                        return _dispatch("open_url", {"target": app_name}, user_text)
                    return message_result("error", "privacy_web_blocked")
            do = app_launcher.launch if action == "launch" else app_launcher.close
            ok, label = do(app_name)
            if ok:
                key = "app_launched" if action == "launch" else "app_closed"
                return message_result("ok", key, name=label)
            # Exact match failed — try fuzzy
            candidates = app_launcher.find_candidates(app_name)
            if len(candidates) == 1:
                ok2, label2 = do(candidates[0])
                if action == "launch":
                    key = "app_launched" if ok2 else "app_not_found"
                else:
                    key = "app_closed" if ok2 else "app_close_failed"
                return message_result("ok" if ok2 else "not_found", key, name=label2)
            if len(candidates) > 1:
                with _context_lock:
                    _pending_choice = PendingChoice(action, tuple(candidates))
                return ToolResult("needs_choice", {"kind": "app_choices", "candidates": candidates})
            # Zero candidates. For launch, retry with hints (and URL hint if
            # the name matches a known web shortcut). For close, just report.
            if action == "close":
                return message_result("not_found", "app_close_failed", name=app_name)
            retry_ctx = _build_launch_retry_context(app_name, user_text)
            if url_shortcuts.is_known(app_name):
                retry_ctx = (
                    retry_ctx + "\n\n"
                    + locales.get("retry_launch_url_hint", name=app_name)
                )
            return message_result("not_found", "app_not_found",
                                  retry_context=retry_ctx, name=app_name)

        elif name == "search_files":
            folder = (args.get("folder") or "").strip()
            query = (args.get("query") or "").strip()
            include_date = bool(args.get("include_date", False))
            include_size = bool(args.get("include_size", False))
            r = file_search.search(folder, query,
                                   include_size=include_size,
                                   include_date=include_date)
            if r["folder_resolved"] is None:
                return message_result("not_found", "folder_unknown", name=folder)
            results = r["found"] or r["similar"]
            if not results:
                return message_result("not_found", "file_no_results",
                                      folder=r["folder_resolved"], query=query)
            # Set multi-turn state so a numbered reply opens a file.
            paths = [item["path"] for item in results]
            with _context_lock:
                _pending_choice = PendingChoice("open_file", tuple(paths))
            visible = [{key: value for key, value in item.items() if key != "path"}
                       for item in results]
            return ToolResult("needs_choice", {"kind": "file_choices",
                              "folder": r["folder_resolved"], "query": query,
                              "found": bool(r["found"]), "results": visible})

        elif name == "open_url":
            target = (args.get("target") or "").strip()
            url = url_shortcuts.resolve(target)
            if not url:
                return message_result("not_found", "url_invalid", target=target)
            try:
                subprocess.Popen(
                    ["xdg-open", url],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            except Exception as exc:
                return message_result("error", "url_invalid", target=target)
            # TTS-friendly: return the spoken keyword if it's a known shortcut,
            # else extract just the hostname stem ("https://www.example.com/x"
            # → "example"). Avoids reading "https colon slash slash..." aloud.
            if url_shortcuts.is_known(target):
                display = target
            else:
                from urllib.parse import urlparse
                host = urlparse(url).netloc.removeprefix("www.")
                display = host.split(".")[0] if host else target
            return message_result("ok", "url_opened", url=display)

        elif name == "open_folder":
            folder_name = (args.get("name") or "").strip()
            path = folders.resolve(folder_name)
            if path is None:
                return message_result("not_found", "folder_unknown", name=folder_name)
            if not path.exists():
                return message_result("not_found", "folder_missing", path=str(path))
            try:
                subprocess.Popen(
                    ["xdg-open", str(path)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            except Exception:
                return message_result("error", "folder_missing", path=str(path))
            # TTS-friendly: pass the keyword the user actually said rather than
            # the absolute filesystem path (which would be read literally).
            return message_result("ok", "folder_opened", path=folder_name)

        else:
            return message_result("error", "unknown_command", name=name)

    except Exception as exc:
        log.error("Dispatch error: %s", type(exc).__name__)
        return message_result("error", "assistant_error")


def _render_tool_result(result: ToolResult) -> str:
    """Localize application-owned data after execution, without altering IDs."""
    global _last_spoken_result
    data = result.data
    kind = data["kind"]
    if kind == "message":
        return locales.get(data["key"], **data["params"])
    if kind == "web_results":
        return "\n\n".join(f"**{r['title']}**\n{r['body']}\n{r['href']}"
                           for r in data["results"])
    if kind == "vault_results":
        return "\n\n".join(f"**{r['title']}**\n{r['excerpt']}"
                           for r in data["results"])
    if kind == "app_choices":
        lines = "\n".join(f"{i}: {name}" for i, name in
                          enumerate(data["candidates"], 1))
        return locales.get("app_candidates", list=lines)
    if kind == "file_choices":
        lines = []
        for i, item in enumerate(data["results"], 1):
            extras = []
            if "mtime" in item:
                extras.append(item["mtime"])
            if "size_kb" in item:
                extras.append(f"{item['size_kb']} KB")
            if "matched" in item:
                extras.append("partial: " + ", ".join(item["matched"]))
            suffix = f" ({'; '.join(extras)})" if extras else ""
            lines.append(f"{i}. {item['name']}{suffix}")
        _last_spoken_result = locales.get("file_results_spoken", count=len(lines))
        key = "file_results_found" if data["found"] else "file_results_similar"
        return locales.get(key, folder=data["folder"], query=data["query"],
                           list="\n".join(lines))
    raise ValueError(f"unknown tool result kind: {kind}")


# ── Public API ────────────────────────────────────────────────────────────

def ping_llama_server() -> bool:
    """Quick connectivity check. Returns True if LLM backend is reachable."""
    return _get_backend().ping()


def reload_backend():
    reset_context()
    log.info("LLM configuration changed; conversation cleared.")


def process(text: str) -> str:
    """Process transcribed text through llama-server. Returns answer string."""
    global _conversation_history, _last_interaction, _pending_choice

    global _history_policy, _history_has_local_data
    turn_local_data = False
    policy_key = privacy.state_key()
    if policy_key != _history_policy:
        reset_context()
        _history_policy = policy_key
    backend = _get_backend()
    privacy.check_endpoint(backend._url)
    log_content("Assistant input: %r", text)

    global _last_was_synthesised, _last_spoken_result, _last_source_refs
    _last_was_synthesised = False
    _last_spoken_result = ""
    _last_source_refs = []

    # Hardcoded shortcut: clear context request bypasses the LLM entirely.
    # Saves a tool slot for the small model and is unambiguous on the listed
    # phrasings.
    if _is_clear_context_request(text):
        reset_context()
        return locales.get("context_cleared")
    if _is_negated_action(text):
        return locales.get("action_negated")
    if _has_two_explicit_targets(text):
        return locales.get("one_action")

    # Snapshot mutable state under the lock
    with _context_lock:
        pending        = _pending_choice
        waiting        = pending is not None
        candidates     = pending.candidates if pending else ()
        action         = pending.action if pending else ""
        history        = list(_conversation_history)
        history_local  = _history_has_local_data
        last_time      = _last_interaction

    # Auto-reset on timeout
    now = _time.monotonic()
    if history and (now - last_time) > _CONTEXT_TIMEOUT:
        log.info("Context timeout — resetting conversation")
        reset_context()
        with _context_lock:
            history  = []
            history_local = False
            waiting  = False

    # Resolve pending numbered reply
    if waiting:
        n = _parse_number(text)
        if n is not None and 1 <= n <= len(candidates):
            if action in ("open_file", "launch", "close"):
                privacy.check_endpoint(backend._url, local_data=True)
            chosen = candidates[n - 1]
            log_content("Resolving candidate %d: %s (action=%s)", n, chosen, action)
            with _context_lock:
                _pending_choice = None
            if action == "open_file":
                # `chosen` is an absolute file path here, not an app name.
                from pathlib import Path as _Path
                p = _Path(chosen)
                if not p.exists():
                    result = locales.get("file_open_failed", path=chosen)
                else:
                    try:
                        subprocess.Popen(
                            ["xdg-open", chosen],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True,
                        )
                        result = locales.get("file_opened", name=p.name)
                    except Exception:
                        result = locales.get("file_open_failed", path=chosen)
            elif action == "launch":
                ok, label = app_launcher.launch(chosen)
                result = locales.get("app_launched", name=label) if ok else locales.get("app_not_found", name=label)
            else:
                ok, label = app_launcher.close(chosen)
                result = locales.get("app_closed", name=label) if ok else locales.get("app_close_failed", name=label)
            with _context_lock:
                _history_has_local_data = True
                _conversation_history.append({"role": "user",      "content": text})
                _conversation_history.append({"role": "assistant",  "content": result})
                if len(_conversation_history) > 16:
                    _conversation_history = _conversation_history[-16:]
                _last_interaction = _time.monotonic()
            return result
        else:
            # Not a valid number — drop waiting state and process normally
            with _context_lock:
                _pending_choice = None

    # Normal LLM flow (with history for multi-turn)
    messages = [{"role": "system", "content": _system_prompt()}] + history + [
        {"role": "user", "content": text},
    ]
    available_tools = _get_tools()
    started = _time.perf_counter()
    _llm_manager.ensure_running()
    startup_ms = (_time.perf_counter() - started) * 1000
    started = _time.perf_counter()
    data = backend.chat(messages=messages, tools=available_tools, local_data=history_local,
                        max_tokens=512)
    llm_ms = (_time.perf_counter() - started) * 1000
    tool_ms = 0.0

    if data is None:
        return locales.get("not_understood")

    result = locales.get("not_understood")
    repair_used = False
    try:
        choices = data.get("choices", [])
        if not choices:
            return locales.get("not_understood")

        if choices[0].get("finish_reason") == "length":
            return locales.get("not_understood")
        msg = choices[0].get("message") or {}
        tool_calls = msg.get("tool_calls")

        if tool_calls:
            if not isinstance(tool_calls, list) or len(tool_calls) != 1:
                return locales.get("one_action")
            tc = tool_calls[0]
            fn_name = (tc.get("function") or {}).get("name")
            if fn_name in _WEB_TOOLS:
                privacy.require_web()
            if fn_name in _LOCAL_TOOLS:
                privacy.check_endpoint(backend._url, local_data=True)
            try:
                fn_name, args = validate_call(tc, available_tools)
            except InvalidToolCall as exc:
                repair_used = True
                repair_messages = messages + [{"role": "assistant", "content": str(msg.get("content") or "")},
                                              {"role": "user", "content": (
                                                  "Your tool call was invalid (" + str(exc) + "). "
                                                  "Return exactly one valid tool call or ask a short clarification."
                                              )}]
                repair_data = backend.chat(messages=repair_messages, tools=available_tools,
                                           local_data=history_local, max_tokens=256)
                if not repair_data:
                    return locales.get("not_understood")
                repair_choices = repair_data.get("choices") or []
                if not repair_choices or repair_choices[0].get("finish_reason") == "length":
                    return locales.get("not_understood")
                repair_msg = repair_choices[0].get("message") or {}
                repair_calls = repair_msg.get("tool_calls") or []
                if len(repair_calls) != 1:
                    return locales.get("one_action") if repair_calls else locales.get("not_understood")
                tc = repair_calls[0]
                fn_name = (tc.get("function") or {}).get("name")
                if fn_name in _WEB_TOOLS:
                    privacy.require_web()
                if fn_name in _LOCAL_TOOLS:
                    privacy.check_endpoint(backend._url, local_data=True)
                try:
                    fn_name, args = validate_call(tc, available_tools)
                except InvalidToolCall:
                    return locales.get("not_understood")
            turn_local_data = fn_name in _LOCAL_TOOLS
            started = _time.perf_counter()
            tool_result = _dispatch(fn_name, args, user_text=text)
            tool_ms += (_time.perf_counter() - started) * 1000
            raw_result = _render_tool_result(tool_result)
            retry_ctx = tool_result.retry_context

            # Launch retry: LLM hit a not-found — give it candidate apps and
            # let it try again once. No further retry from that second call.
            if retry_ctx is not None and not repair_used:
                log.info("launch_app retry: feeding %d chars of context back to LLM", len(retry_ctx))
                tool_call_id = tc.get("id", "tc_0")
                retry_messages = messages + [
                    {"role": "assistant", "tool_calls": [tc]},
                    {"role": "tool", "tool_call_id": tool_call_id, "content": retry_ctx},
                ]
                started = _time.perf_counter()
                retry_data = backend.chat(messages=retry_messages, tools=available_tools,
                                          local_data=True, max_tokens=256)
                llm_ms += (_time.perf_counter() - started) * 1000
                if retry_data:
                    try:
                        retry_choice = retry_data.get("choices", [{}])[0]
                        if retry_choice.get("finish_reason") == "length":
                            return raw_result
                        retry_msg = retry_choice.get("message") or {}
                        retry_tcs = retry_msg.get("tool_calls")
                        if retry_tcs:
                            if len(retry_tcs) != 1:
                                return locales.get("one_action")
                            retry_fn = (retry_tcs[0].get("function") or {}).get("name")
                            if retry_fn in _WEB_TOOLS:
                                privacy.require_web()
                            if retry_fn in _LOCAL_TOOLS:
                                privacy.check_endpoint(backend._url, local_data=True)
                            retry_fn, retry_args = validate_call(retry_tcs[0], available_tools)
                            # Execute once, ignore any further retry_ctx to avoid loops
                            turn_local_data |= retry_fn in _LOCAL_TOOLS
                            started = _time.perf_counter()
                            retry_result = _dispatch(retry_fn, retry_args, user_text=text)
                            tool_ms += (_time.perf_counter() - started) * 1000
                            retry_text = _render_tool_result(retry_result)
                            if retry_text:
                                raw_result = retry_text
                        else:
                            retry_content = (retry_msg.get("content") or "").strip()
                            if retry_content:
                                log_content("Retry text response: %s", retry_content[:120])
                                raw_result = retry_content
                    except (InvalidToolCall, KeyError, IndexError, TypeError) as exc:
                        log.error("Retry parsing error: %s", exc)
                else:
                    log.warning("Retry returned None — using original not-found message")

            # Search tools: feed results back to LLM for a concise synthesis
            elif fn_name in _SEARCH_TOOLS and _last_source_refs:
                tool_call_id = tc.get("id", "tc_0")
                synthesis_messages = messages + [
                    {"role": "assistant", "tool_calls": [tc]},
                    {"role": "tool", "tool_call_id": tool_call_id,
                     "content": json.dumps({"status": tool_result.status,
                                            "data": tool_result.data}, ensure_ascii=False)},
                ]
                started = _time.perf_counter()
                syn_data = backend.chat(messages=synthesis_messages, tools=None,
                                         local_data=history_local or fn_name != "search_web",
                                         max_tokens=384)
                llm_ms += (_time.perf_counter() - started) * 1000
                if syn_data:
                    syn_choices = syn_data.get("choices", [])
                    if syn_choices and syn_choices[0].get("finish_reason") != "length":
                        syn_content = (syn_choices[0]
                                       .get("message") or {}).get("content") or ""
                        syn_content = (syn_content
                                       .strip())
                        if syn_content:
                            log_content("Synthesis: %s", syn_content[:120])
                            _last_spoken_result = syn_content
                            raw_result = syn_content
                            if _last_source_refs:
                                raw_result += "\n\n" + locales.get("sources") + ":\n"
                                raw_result += "\n".join(f"{i}. {ref}" for i, ref in
                                                        enumerate(_last_source_refs, 1))
                            _last_was_synthesised = True
                        else:
                            log.warning("Synthesis empty — using raw result")
                else:
                    log.warning("Synthesis returned None — using raw result")

            result = raw_result

        else:
            # No tool call: plain text response
            content = (msg.get("content") or "").strip()
            if content:
                log_content("LLM text response: %s", content)
                result = content

    except (KeyError, IndexError, TypeError) as exc:
        log.error("Response parsing error: %s", exc)
        return locales.get("not_understood")

    # Append this turn to history.
    post_started = _time.perf_counter()
    with _context_lock:
        _history_has_local_data |= turn_local_data
        _conversation_history.append({"role": "user",      "content": text})
        _conversation_history.append({"role": "assistant",  "content": result})
        if len(_conversation_history) > 16:
            _conversation_history = _conversation_history[-16:]
        _last_interaction = _time.monotonic()

    log.info("Assistant stages: model_startup=%.1fms llm_response=%.1fms "
             "tool_execution=%.1fms postprocessing=%.1fms",
             startup_ms, llm_ms, tool_ms,
             (_time.perf_counter() - post_started) * 1000)

    return result
