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
import privacy
from llm_profiles import profile


@runtime_checkable
class LLMBackend(Protocol):
    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        *, local_data: bool = False, max_tokens: int = 256,
    ) -> dict | None:
        """Send messages to the LLM. Returns normalized response dict or None on error."""
        ...


class LlamaServerBackend:
    """HTTP client for llama-server / Ollama (OpenAI-compatible /v1/chat/completions)."""

    def __init__(self, base_url: str, model: str, api_key: str = "",
                 provider: str = "llama_cpp"):
        base = base_url.rstrip("/")
        self._url = base + ("" if base.endswith("/v1") else "/v1") + "/chat/completions"
        self._model = model
        self._api_key = api_key  # empty for local; Bearer token for cloud
        self._provider = provider

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        *, local_data: bool = False, max_tokens: int = 256,
    ) -> dict | None:
        url = privacy.check_endpoint(self._url, local_data=local_data)
        try:
            import httpx
        except ImportError:
            log.error("httpx not installed — cannot call LLM backend")
            return None

        body: dict = {"model": self._model, "messages": messages,
                      "max_tokens": max_tokens}
        body.update(profile(self._model, self._provider))
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            with httpx.Client(timeout=60, trust_env=False) as client:
                resp = client.post(url, json=body, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            log.error("LLM backend request failed: %s", type(exc).__name__)
            return None

        _normalize_hermes_tool_calls(data)
        _strip_reasoning(data)
        return data

    def ping(self) -> bool:
        """Quick connectivity check. Returns True if backend is reachable."""
        try:
            url = privacy.check_endpoint(self._url)
        except privacy.PolicyError:
            return False
        try:
            import httpx
            base = url.rsplit("/v1/", 1)[0]
            headers = {}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            with httpx.Client(timeout=5, trust_env=False) as client:
                # Ollama local has /health, Ollama Cloud has /v1/models
                resp = client.get(f"{base}/health", headers=headers)
                if resp.status_code == 200:
                    return True
        except Exception:
            pass
        # Fallback: try /v1/models (Ollama Cloud, OpenAI-compatible)
        try:
            import httpx
            models_url = url.rsplit("/chat/", 1)[0] + "/models"
            headers = {}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            with httpx.Client(timeout=5, trust_env=False) as client:
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
        if not isinstance(content, str):
            return
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

        if not isinstance(data, dict):
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


def _strip_reasoning(data: dict) -> None:
    """Never expose in-band thinking text to the overlay or TTS."""
    try:
        message = data["choices"][0]["message"]
        content = message.get("content")
        if not isinstance(content, str):
            return
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
        if "<think>" in content:
            content = content.split("<think>", 1)[0]
        message["content"] = content.strip() or None
    except (KeyError, IndexError, TypeError):
        return
