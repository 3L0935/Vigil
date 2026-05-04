"""URL shortcuts registry for the open_url tool.

Maps short names ('youtube', 'github', ...) to canonical URLs. Users speak,
they don't dictate URLs — so the LLM passes a keyword and we resolve it
here. Raw URLs / bare domains are also accepted as a quiet fallback for
text-mode usage but the voice path only ever needs keyword lookup.

Keep the registry small and high-signal — these are the sites users
actually ask for by name, not a comprehensive web index.
"""

from __future__ import annotations
import re

_SHORTCUTS: dict[str, str] = {
    # Video / streaming
    "youtube":      "https://youtube.com",
    "yt":           "https://youtube.com",
    "netflix":      "https://netflix.com",
    "twitch":       "https://twitch.tv",
    "primevideo":   "https://primevideo.com",
    "disneyplus":   "https://disneyplus.com",

    # Music
    "spotify":      "https://open.spotify.com",
    "soundcloud":   "https://soundcloud.com",
    "deezer":       "https://deezer.com",

    # Dev
    "github":       "https://github.com",
    "gitlab":       "https://gitlab.com",
    "stackoverflow": "https://stackoverflow.com",
    "huggingface":  "https://huggingface.co",

    # Email
    "gmail":        "https://mail.google.com",
    "outlook":      "https://outlook.live.com",
    "protonmail":   "https://mail.proton.me",
    "proton":       "https://mail.proton.me",

    # Social
    "twitter":      "https://twitter.com",
    "x":            "https://x.com",
    "facebook":     "https://facebook.com",
    "instagram":    "https://instagram.com",
    "linkedin":     "https://linkedin.com",
    "reddit":       "https://reddit.com",
    "tiktok":       "https://tiktok.com",
    "bluesky":      "https://bsky.app",
    "mastodon":     "https://mastodon.social",

    # Shopping (FR-leaning defaults)
    "amazon":       "https://amazon.fr",
    "aliexpress":   "https://aliexpress.com",
    "vinted":       "https://vinted.fr",
    "leboncoin":    "https://leboncoin.fr",

    # AI
    "chatgpt":      "https://chat.openai.com",
    "claude":       "https://claude.ai",
    "gemini":       "https://gemini.google.com",
    "perplexity":   "https://perplexity.ai",

    # Reference / search
    "wikipedia":    "https://wikipedia.org",
    "wiki":         "https://wikipedia.org",
    "duckduckgo":   "https://duckduckgo.com",
    "kagi":         "https://kagi.com",
    "google":       "https://google.com",

    # Productivity
    "drive":        "https://drive.google.com",
    "googledrive":  "https://drive.google.com",
    "maps":         "https://maps.google.com",
    "googlemaps":   "https://maps.google.com",
    "notion":       "https://notion.so",

    # Communication (web clients)
    "discord":      "https://discord.com/app",
    "slack":        "https://slack.com",
    "whatsapp":     "https://web.whatsapp.com",
    "telegram":     "https://web.telegram.org",
}


def _normalise_key(name: str) -> str:
    """Lowercase, strip whitespace and trailing punctuation, collapse spaces."""
    return re.sub(r"\s+", "", name.strip().lower().rstrip(".,!?;:"))


def lookup(name: str) -> str | None:
    """Return the canonical URL for a known shortcut, else None."""
    return _SHORTCUTS.get(_normalise_key(name))


def is_known(name: str) -> bool:
    return _normalise_key(name) in _SHORTCUTS


def resolve(target: str) -> str | None:
    """Resolve a user-supplied target to a launchable URL.

    Order: (1) known shortcut, (2) string already looks like a URL (http/https
    or has a TLD-like suffix), (3) bare 'something.tld'-style → prepend https://.
    Returns None if nothing matches and the target doesn't look web-like.
    """
    if not target:
        return None
    s = target.strip()
    hit = lookup(s)
    if hit:
        return hit
    if s.startswith(("http://", "https://")):
        return s
    # Bare domain heuristic: contains a dot, no spaces, looks like host.tld[/path]
    if " " not in s and re.match(r"^[\w\-]+(\.[\w\-]+)+(/.*)?$", s):
        return f"https://{s}"
    return None
