import json
from unittest.mock import Mock

import pytest

import assistant
import file_search
import privacy


def tool(name, args, *, extra=False, finish_reason="tool_calls"):
    calls = [{"id": "one", "type": "function",
              "function": {"name": name, "arguments": json.dumps(args)}}]
    if extra:
        calls.append(calls[0])
    return {"choices": [{"finish_reason": finish_reason,
                         "message": {"tool_calls": calls}}]}


@pytest.fixture
def flow(monkeypatch):
    class Backend:
        _url = "http://localhost:8081/v1/chat/completions"
        def __init__(self):
            self.responses = []
            self.calls = []
        def chat(self, **kwargs):
            self.calls.append(kwargs)
            return self.responses.pop(0)
    backend = Backend()
    manager = Mock()
    monkeypatch.setattr(assistant, "_get_backend", lambda: backend)
    monkeypatch.setattr(assistant._llm_manager, "ensure_running", manager)
    monkeypatch.setattr(privacy, "check_endpoint", lambda url, **kw: url)
    monkeypatch.setattr(privacy, "local_tools_allowed", lambda url: True)
    monkeypatch.setattr(privacy, "web_allowed", lambda: True)
    monkeypatch.setattr(privacy, "require_web", lambda: None)
    assistant.reset_context()
    assistant._history_policy = None
    return backend, manager


def test_explicit_reset_uses_no_inference_but_negated_reset_does(flow):
    backend, manager = flow
    assert assistant.process("clear context")
    assert not backend.calls
    manager.assert_not_called()
    backend.responses.append({"choices": [{"message": {"content": "Okay"}}]})
    assert assistant.process("don't clear context") == "Okay"
    assert len(backend.calls) == 1


def test_file_results_do_not_trigger_synthesis_and_keep_order(flow, monkeypatch, tmp_path):
    backend, manager = flow
    paths = [tmp_path / "invoice-a.pdf", tmp_path / "invoice-b.pdf"]
    monkeypatch.setattr(file_search, "search", lambda *a, **kw: {
        "folder_resolved": "Downloads", "found": [
            {"name": p.name, "path": str(p)} for p in paths], "similar": []})
    backend.responses.append(tool("search_files", {"folder": "downloads", "query": "invoice"}))
    result = assistant.process("Find invoice in downloads")
    assert result.index("invoice-a.pdf") < result.index("invoice-b.pdf")
    assert len(backend.calls) == 1
    assert manager.call_count == 1
    assert assistant._pending_candidates == [str(p) for p in paths]
    assert assistant._parse_number("n'ouvre pas la deuxième") is None


def test_pending_selection_does_not_start_model(flow, monkeypatch):
    backend, manager = flow
    launch = Mock(return_value=(True, "Second"))
    monkeypatch.setattr(assistant.app_launcher, "launch", launch)
    assistant._waiting_for_reply = True
    assistant._pending_candidates = ["First", "Second"]
    assistant._pending_action = "launch"
    assistant._history_policy = privacy.state_key()
    assert "Second" in assistant.process("ouvre la deuxième")
    launch.assert_called_once_with("Second")
    manager.assert_not_called()
    assert not backend.calls


def test_multiple_or_truncated_calls_have_no_effect(flow, monkeypatch):
    backend, _ = flow
    launch = Mock()
    monkeypatch.setattr(assistant.app_launcher, "launch", launch)
    backend.responses.extend([
        tool("app_action", {"name": "Firefox", "action": "launch"}, extra=True),
        tool("app_action", {"name": "Firefox", "action": "launch"}, finish_reason="length"),
    ])
    assert assistant.process("Open two apps") == assistant.locales.get("one_action")
    assert assistant.process("Open Firefox") == assistant.locales.get("not_understood")
    launch.assert_not_called()


def test_invalid_action_repair_is_bounded_before_execution(flow, monkeypatch):
    backend, _ = flow
    launch = Mock(return_value=(True, "Firefox"))
    monkeypatch.setattr(assistant.app_launcher, "launch", launch)
    bad = tool("app_action", {"name": "Firefox", "action": "launchh"})
    backend.responses.extend([bad, bad])
    assert assistant.process("Open Firefox") == assistant.locales.get("not_understood")
    assert len(backend.calls) == 2
    launch.assert_not_called()
