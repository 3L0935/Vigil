"""LLM backend abstraction for Vigil.

Provides a thin Protocol + LlamaServerBackend for standalone use.
Future: swap in LMAgentDaemonBackend to route through LMAgent-plus
without changing any other code.
"""

from __future__ import annotations

import json
import re
from typing import Protocol, runtime_checkable

from logger import log


@runtime_checkable
class LLMBackend(Protocol):
    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> dict | None:
        """Send messages to the LLM. Returns normalized response dict or None on error."""
        ...


class LlamaServerBackend:
    """HTTP client for llama-server / Ollama (OpenAI-compatible /v1/chat/completions)."""

    def __init__(self, base_url: str, model: str, api_key: str = ""):
        self._url = base_url.rstrip("/") + "/v1/chat/completions"
        self._model = model
        self._api_key = api_key  # empty for local; Bearer token for cloud

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> dict | None:
        try:
            import httpx
        except ImportError:
            log.error("httpx not installed — cannot call LLM backend")
            return None

        body: dict = {"model": self._model, "messages": messages}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            with httpx.Client(timeout=60) as client:
                resp = client.post(self._url, json=body, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            log.error("LLM backend request failed: %s", exc)
            return None

        _normalize_hermes_tool_calls(data)
        return data

    def ping(self) -> bool:
        """Quick connectivity check. Returns True if backend is reachable."""
        try:
            import httpx
            base = self._url.rsplit("/v1/", 1)[0]
            headers = {}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            with httpx.Client(timeout=5) as client:
                # Ollama local has /health, Ollama Cloud has /v1/models
                resp = client.get(f"{base}/health", headers=headers)
                if resp.status_code == 200:
                    return True
        except Exception:
            pass
        # Fallback: try /v1/models (Ollama Cloud, OpenAI-compatible)
        try:
            import httpx
            models_url = self._url.rsplit("/chat/", 1)[0] + "/models"
            headers = {}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            with httpx.Client(timeout=5) as client:
                resp = client.get(models_url, headers=headers)
                return resp.status_code == 200
        except Exception:
            return False


# ── Future: LMAgent-plus integration ─────────────────────────────────────────
# To route through LMAgent-plus daemon instead, add this class and swap it in:
#
# class LMAgentDaemonBackend:
#     """Routes via LMAgent-plus JSON-RPC 2.0 WebSocket (ws://127.0.0.1:7771)."""
#     def __init__(self, ws_url: str = "ws://127.0.0.1:7771"): ...
#     def chat(self, messages, tools=None): ...   # websockets + json-rpc call
#
# Then in assistant.py: _backend = LMAgentDaemonBackend()


# ── Hermes XML tool call normalization ────────────────────────────────────────

def _normalize_hermes_tool_calls(data: dict) -> None:
    """Detect and normalize Hermes-style XML tool calls in-place.

    Some models (Hermes, Harmonic) output tool calls as:
        <tool_call>{"name": "tool", "arguments": {...}}</tool_call>
    instead of the OpenAI structured format.
    """
    try:
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        if msg.get("tool_calls"):
            return  # already structured

        content = msg.get("content") or ""
        hermes_calls = _parse_hermes_tool_calls(content)
        if not hermes_calls:
            return

        msg["tool_calls"] = hermes_calls
        # Strip <tool_call> blocks from content
        cleaned = re.sub(r'<tool_call>.*?</tool_call>', '', content, flags=re.DOTALL).strip()
        msg["content"] = cleaned or None
    except (IndexError, KeyError, TypeError):
        pass


def _parse_hermes_tool_calls(text: str) -> list[dict] | None:
    """Extract tool calls from Hermes-style XML format."""
    from json_repair import repair_json

    pattern = re.compile(r'<tool_call>\s*(\{.*?\})\s*</tool_call>', re.DOTALL)
    matches = pattern.findall(text)
    if not matches:
        return None

    tool_calls = []
    for i, raw in enumerate(matches):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = repair_json(raw)
            if data is None:
                continue

        name = data.get("name", "")
        arguments = data.get("arguments", {})
        if isinstance(arguments, dict):
            arguments = json.dumps(arguments)

        if name:
            tool_calls.append({
                "id": f"hermes_{i}",
                "type": "function",
                "function": {"name": name, "arguments": arguments},
            })

    return tool_calls if tool_calls else None
