from unittest.mock import Mock

import pytest

import privacy


@pytest.fixture(autouse=True)
def policy(monkeypatch):
    values = {}
    monkeypatch.setattr(privacy.db, 'get_setting', lambda key, default='': values.get(key, default))
    return values


@pytest.mark.parametrize('url', ['http://127.0.0.1:8081', 'http://localhost:11434', 'http://[::1]:8080/v1'])
def test_loopback_allowed_without_resolving_remote_hosts(url):
    assert privacy.check_endpoint(url)


@pytest.mark.parametrize('url', ['https://example.com', 'http://192.168.1.2:8080', 'http://localhost.example.com', 'file:///tmp/model', 'http://user:secret@localhost', 'http://127.0.0.1@evil.test'])
def test_strict_mode_blocks_remote_and_invalid_urls(url):
    with pytest.raises(privacy.PolicyError):
        privacy.check_endpoint(url)


def test_remote_inference_does_not_imply_local_data_sharing(policy):
    policy['local_only'] = 'false'
    privacy.check_endpoint('https://example.com')
    with pytest.raises(privacy.PolicyError):
        privacy.check_endpoint('https://example.com', local_data=True)
    policy['share_local_data'] = 'true'
    privacy.check_endpoint('https://example.com', local_data=True)


def test_web_requires_both_permissions(policy):
    policy['allow_web'] = 'true'
    assert not privacy.web_allowed()
    policy['local_only'] = 'false'
    assert privacy.web_allowed()


def test_http_never_runs_when_policy_blocks(monkeypatch):
    from llm_backend import LlamaServerBackend
    client = Mock()
    monkeypatch.setattr('httpx.Client', client)
    backend = LlamaServerBackend('https://example.com', 'model')
    with pytest.raises(privacy.PolicyError):
        backend.chat([{'role':'user', 'content':'private transcript'}])
    assert not backend.ping()
    client.assert_not_called()
