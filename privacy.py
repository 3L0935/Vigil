"""Runtime policy for network requests and disclosure of local tool results."""

from ipaddress import ip_address
from urllib.parse import urlsplit, urlunsplit

import database as db
import locales


class PolicyError(RuntimeError):
    """An operation requires a permission the user has not enabled."""


def enabled(key: str, default: bool = False) -> bool:
    return db.get_setting(key, 'true' if default else 'false') == 'true'


def local_only() -> bool:
    return enabled('local_only', True)


def is_loopback(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname:
            return False
        if parsed.username is not None or parsed.password is not None:
            return False
        if parsed.hostname.lower() == 'localhost':
            return True
        return ip_address(parsed.hostname).is_loopback
    except ValueError:
        return False


def check_endpoint(url: str, *, local_data: bool = False) -> str:
    """Return a validated URL; pin localhost to loopback without DNS lookup."""
    try:
        parsed = urlsplit(url)
        valid = (parsed.scheme in ('http', 'https') and parsed.hostname
                 and parsed.username is None and parsed.password is None)
        port = parsed.port  # validates malformed ports before a request
    except ValueError:
        valid = False
    if not valid:
        raise PolicyError(locales.get('privacy_bad_url'))
    local = is_loopback(url)
    if not local and local_only():
        raise PolicyError(locales.get('privacy_remote_blocked'))
    if local_data and not local and not enabled('share_local_data'):
        raise PolicyError(locales.get('privacy_data_blocked'))
    if parsed.hostname.lower() == 'localhost':
        netloc = '127.0.0.1' + (f':{port}' if port is not None else '')
        return urlunsplit(parsed._replace(netloc=netloc))
    return url


def web_allowed() -> bool:
    return not local_only() and enabled('allow_web')


def require_web() -> None:
    if not web_allowed():
        raise PolicyError(locales.get('privacy_web_blocked'))


def local_tools_allowed(endpoint: str) -> bool:
    return is_loopback(endpoint) or (not local_only() and enabled('share_local_data'))


def state_key() -> tuple:
    """Changes invalidate conversational history, including pending choices."""
    keys = ('llm_provider', 'llama_server_url', 'llama_model', 'ollama_local_url',
            'ollama_cloud_url', 'ollama_model', 'local_only', 'allow_web',
            'share_local_data', 'obsidian_vault_path')
    return tuple(db.get_setting(key, '') for key in keys)
