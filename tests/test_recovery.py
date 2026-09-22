from datetime import datetime, timedelta
import logging

import pytest

import recovery
import logger


@pytest.fixture
def storage(tmp_path, monkeypatch):
    monkeypatch.setattr(recovery, 'RECOVERY_FILE', tmp_path / 'recovery_notes.txt')
    settings = {}
    monkeypatch.setattr(recovery.db, 'get_setting', lambda key, default='': settings.get(key,default))
    return settings


def test_recovery_retention_prunes_old_data(storage):
    old = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S')
    recovery.RECOVERY_FILE.write_text(f'[{old}] expired\n')
    assert recovery.save('new\nparagraph')
    text = recovery.RECOVERY_FILE.read_text()
    assert 'expired' not in text
    assert 'new' in text and 'paragraph' in text
    assert recovery.RECOVERY_FILE.stat().st_mode & 0o777 == 0o600


def test_disabled_recovery_does_not_persist(storage):
    storage['recovery_days'] = '0'
    assert not recovery.save('private')
    assert not recovery.RECOVERY_FILE.exists()


def test_recovery_is_bounded_and_purge_removes_it(storage, monkeypatch):
    monkeypatch.setattr(recovery, '_MAX_BYTES', 200)
    for _ in range(10):
        recovery.save('a synthetic transcript')
    assert recovery.RECOVERY_FILE.stat().st_size <= 200
    recovery.purge()
    assert not recovery.RECOVERY_FILE.exists()


def test_content_logging_requires_opt_in(caplog):
    with caplog.at_level(logging.INFO, logger='vigil'):
        logger.configure_content_logging(False)
        logger.log_content('Transcript: %s', 'PRIVATE_CONTENT')
        assert 'PRIVATE_CONTENT' not in caplog.text
        logger.configure_content_logging(True)
        logger.log_content('Transcript: %s', 'EXPLICIT_DEBUG')
        assert 'EXPLICIT_DEBUG' in caplog.text
    logger.configure_content_logging(False)
