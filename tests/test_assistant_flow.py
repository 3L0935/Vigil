import json
from unittest.mock import Mock

import pytest

import assistant
from assistant_tools import PendingChoice
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


def test_negated_and_two_target_commands_do_not_start_model(flow):
    backend, manager = flow
    assert assistant.process("N'ouvre pas Firefox") == assistant.locales.get('action_negated')
    assert assistant.process("Ne lance pas Firefox") == assistant.locales.get('action_negated')
    assert assistant.process("Ouvre Firefox et VLC") == assistant.locales.get('one_action')
    assert not backend.calls
    manager.assert_not_called()


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
    assert assistant._pending_choice.candidates == tuple(str(p) for p in paths)
    assert assistant._parse_number("n'ouvre pas la deuxième") is None
    structured = assistant._dispatch('search_files', {'folder': 'downloads', 'query': 'invoice'})
    assert structured.status == 'needs_choice'
    assert [item['name'] for item in structured.data['results']] == [
        'invoice-a.pdf', 'invoice-b.pdf']
    assert all('path' not in item for item in structured.data['results'])


def test_pending_selection_does_not_start_model(flow, monkeypatch):
    backend, manager = flow
    launch = Mock(return_value=(True, "Second"))
    monkeypatch.setattr(assistant.app_launcher, "launch", launch)
    assistant._pending_choice = PendingChoice("launch", ("First", "Second"))
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


def test_named_web_service_does_not_fuzzy_launch_an_unrelated_app(flow, monkeypatch):
    backend, _ = flow
    open_process = Mock()
    launch = Mock()
    monkeypatch.setattr(assistant.app_launcher, 'list_all_apps', lambda: [])
    monkeypatch.setattr(assistant.app_launcher, 'launch', launch)
    monkeypatch.setattr(assistant.subprocess, 'Popen', open_process)
    backend.responses.append(tool('app_action', {'name': 'YouTube', 'action': 'launch'}))
    assert 'YouTube' in assistant.process('Ouvre YouTube')
    launch.assert_not_called()
    assert open_process.call_args.args[0][0] == 'xdg-open'
    assert len(backend.calls) == 1


def test_named_web_service_respects_web_permission(flow, monkeypatch):
    backend, _ = flow
    monkeypatch.setattr(assistant.app_launcher, 'list_all_apps', lambda: [])
    launch = Mock()
    monkeypatch.setattr(assistant.app_launcher, 'launch', launch)
    monkeypatch.setattr(privacy, 'web_allowed', lambda: False)
    backend.responses.append(tool('app_action', {'name': 'YouTube', 'action': 'launch'}))
    assert assistant.process('Ouvre YouTube') == assistant.locales.get('privacy_web_blocked')
    launch.assert_not_called()


def test_web_synthesis_retains_application_owned_source(flow, monkeypatch):
    import sys
    from types import SimpleNamespace
    backend, _ = flow
    class FakeSearch:
        def text(self, query, max_results):
            return [{'title': 'Release note', 'body': 'A bounded excerpt',
                     'href': 'https://example.org/release'}]
    monkeypatch.setitem(sys.modules, 'ddgs', SimpleNamespace(DDGS=FakeSearch))
    backend.responses.extend([
        tool('search_web', {'query': 'release'}),
        {'choices': [{'message': {'content': 'A short summary.'}}]},
    ])
    result = assistant.process('Search the release')
    assert result.startswith('A short summary.')
    assert 'https://example.org/release' in result
    assert assistant.spoken_reply(result) == 'A short summary.'
    assert len(backend.calls) == 2


def test_repair_and_launch_resolution_share_one_retry(flow, monkeypatch):
    backend, _ = flow
    monkeypatch.setattr(assistant.app_launcher, 'launch', lambda name: (False, name))
    monkeypatch.setattr(assistant.app_launcher, 'find_candidates', lambda *a, **kw: [])
    monkeypatch.setattr(assistant.app_launcher, 'list_all_apps', lambda: [])
    backend.responses.extend([
        tool('app_action', {'name': 'Missing App', 'action': 'launchh'}),
        tool('app_action', {'name': 'Missing App', 'action': 'launch'}),
    ])
    assert 'Missing App' in assistant.process('Open Missing App')
    assert len(backend.calls) == 2
