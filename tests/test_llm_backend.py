import json

import httpx

from llm_backend import LlamaServerBackend
from llm_profiles import profile
from llm_backend import _normalize_hermes_tool_calls, _strip_reasoning


def test_profiles_are_specific_to_model_and_provider():
    assert profile("Qwen3-4B-Q4_K_M.gguf", "llama_cpp")["chat_template_kwargs"] == {
        "enable_thinking": False}
    assert "chat_template_kwargs" not in profile("Qwen3.5-4B.gguf", "llama_cpp")
    assert profile("LFM2.5-1.2B-Instruct.gguf", "llama_cpp")["temperature"] == 0.1
    assert profile("LFM2.5-2.6B-Q4_K_M.gguf", "llama_cpp")["repeat_penalty"] == 1.1
    assert profile("LFM2.5-1.2B-Instruct.gguf", "ollama_local") == {}


def test_request_has_budget_and_native_response_is_preserved(monkeypatch):
    requests = []
    real_client = httpx.Client
    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"tool_calls": [
            {"function": {"name": "open_settings", "arguments": "{}"}}]}}]})
    monkeypatch.setattr(httpx, "Client", lambda **kw: real_client(
        transport=httpx.MockTransport(handler), **kw))
    backend = LlamaServerBackend("http://localhost:8081", "Qwen3-4B-Q4_K_M.gguf",
                                 use_model_profile=True)
    result = backend.chat([{"role": "user", "content": "settings"}], max_tokens=256)
    assert result["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "open_settings"
    assert requests[0]["max_tokens"] == 256
    assert requests[0]["chat_template_kwargs"] == {"enable_thinking": False}


def test_compatible_profile_remains_the_default(monkeypatch):
    requests = []
    real_client = httpx.Client
    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})
    monkeypatch.setattr(httpx, "Client", lambda **kw: real_client(
        transport=httpx.MockTransport(handler), **kw))
    backend = LlamaServerBackend("http://localhost:8081", "Qwen3-4B-Q4_K_M.gguf")
    assert backend.chat([{"role": "user", "content": "Hello"}]) is not None
    assert requests[0]["parallel_tool_calls"] is False
    assert "chat_template_kwargs" not in requests[0]
    assert "temperature" not in requests[0]


def test_hermes_call_and_reasoning_are_normalized_without_eval():
    data = {'choices': [{'message': {'content': (
        '<think>internal reasoning</think><tool_call>'
        '{"name":"open_settings","arguments":{}}</tool_call>')}}]}
    _normalize_hermes_tool_calls(data)
    _strip_reasoning(data)
    message = data['choices'][0]['message']
    assert message['tool_calls'][0]['function']['name'] == 'open_settings'
    assert message['content'] is None


def test_null_content_and_unclosed_thinking_do_not_leak():
    data = {'choices': [{'message': {'content': None}}]}
    _normalize_hermes_tool_calls(data)
    _strip_reasoning(data)
    assert data['choices'][0]['message']['content'] is None
    data['choices'][0]['message']['content'] = '<think>unfinished'
    _strip_reasoning(data)
    assert data['choices'][0]['message']['content'] is None
