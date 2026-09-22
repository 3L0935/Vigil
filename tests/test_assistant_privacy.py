import json
from unittest.mock import Mock

import httpx
import pytest

import assistant
import config
import privacy


@pytest.fixture
def setup(monkeypatch, tmp_path):
    import database as db
    settings = {'llm_provider':'ollama_cloud', 'local_only':'false',
                'ollama_cloud_url':'https://cloud.example', 'ollama_model':'test'}
    monkeypatch.setattr(db, 'get_setting', lambda k, default='': settings.get(k,default))
    monkeypatch.setattr(assistant._llm_manager, 'ensure_running', Mock())
    monkeypatch.setattr(config, 'OBSIDIAN_VAULT_PATH', str(tmp_path))
    (tmp_path / 'note.md').write_text('needle PRIVATE_LOCAL_NOTE')
    assistant.reset_context()
    assistant._history_policy = None
    return settings


def fake_http(monkeypatch, responses):
    requests = []
    real_client = httpx.Client
    def handler(req):
        requests.append(json.loads(req.content))
        return httpx.Response(200, json=responses.pop(0))
    factory = Mock(side_effect=lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setattr(httpx, 'Client', factory)
    return requests, factory


def tool(name):
    return {'choices':[{'message':{'tool_calls':[{'id':'test', 'type':'function',
        'function':{'name':name,'arguments':'{"query":"needle"}'}}]}}]}


def answer(text):
    return {'choices':[{'message':{'content':text}}]}


def test_remote_tool_call_cannot_override_local_data_permission(setup, monkeypatch):
    requests, _ = fake_http(monkeypatch, [tool('search_obsidian_vault')])
    with pytest.raises(privacy.PolicyError):
        assistant.process('find needle')
    assert len(requests) == 1
    assert 'PRIVATE_LOCAL_NOTE' not in json.dumps(requests)
    advertised = {t['function']['name'] for t in requests[0]['tools']}
    assert 'search_obsidian_vault' not in advertised
    assert 'search_web' not in advertised


def test_explicit_local_data_permission_allows_synthesis(setup, monkeypatch):
    setup['share_local_data'] = 'true'
    requests, factory = fake_http(monkeypatch, [tool('search_obsidian_vault'), answer('summary')])
    assert assistant.process('find needle') == 'summary'
    assert 'PRIVATE_LOCAL_NOTE' in json.dumps(requests[1])
    assert all(call.kwargs['trust_env'] is False for call in factory.call_args_list)


def test_provider_switch_clears_local_history_before_remote_request(setup, monkeypatch):
    setup['llm_provider'] = 'llama_cpp'
    requests, _ = fake_http(monkeypatch, [answer('PRIVATE_LOCAL_HISTORY'), answer('cloud response')])
    assistant.process('local question')
    setup['llm_provider'] = 'ollama_cloud'
    assistant.process('new question')
    assert 'PRIVATE_LOCAL_HISTORY' not in json.dumps(requests[1])
    assert 'local question' not in json.dumps(requests[1])


def test_fabricated_web_call_still_blocked(setup, monkeypatch):
    requests, _ = fake_http(monkeypatch, [tool('search_web')])
    with pytest.raises(privacy.PolicyError):
        assistant.process('search')
    assert len(requests) == 1


def test_strict_mode_blocks_before_manager_or_http(setup, monkeypatch):
    setup['local_only'] = 'true'
    requests, _ = fake_http(monkeypatch, [])
    with pytest.raises(privacy.PolicyError):
        assistant.process('private dictation')
    assert not requests
    assistant._llm_manager.ensure_running.assert_not_called()


def test_revoking_sharing_mid_request_blocks_local_history(setup, monkeypatch):
    setup['share_local_data'] = 'true'
    requests, _ = fake_http(monkeypatch, [tool('search_obsidian_vault'), answer('PRIVATE_LOCAL_NOTE')])
    assistant.process('find needle')
    assert len(requests) == 2
    def revoke_before_http():
        setup['share_local_data'] = 'false'
        return []
    monkeypatch.setattr(assistant, '_get_tools', revoke_before_http)
    with pytest.raises(privacy.PolicyError):
        assistant.process('follow-up question')
    assert len(requests) == 2
