from dictation_session import LastDictation, DictationSessions


def test_last_dictation_retains_raw_and_final_then_expires():
    now = [100.0]
    last = LastDictation(clock=lambda: now[0])
    assert last.store("roque aime", "ROCm")
    assert last.get() == ("roque aime", "ROCm")
    now[0] += LastDictation.LIFETIME
    assert last.get() is None
    last.clear()


def test_oversized_or_disabled_dictation_replaces_old_without_truncating():
    last = LastDictation()
    assert last.store("old", "old")
    huge = "é" * (LastDictation.MAX_BYTES // 2 + 1)
    assert not last.store(huge, huge)
    assert last.get() is None
    assert last.store("new", "NEW")
    assert not last.store("ignored", "ignored", enabled=False)
    assert last.get() is None
    last.clear()


def test_replacement_timer_cannot_clear_newer_draft():
    last = LastDictation()
    assert last.store("first", "first")
    generation = last._generation
    assert last.store("second", "second")
    last._expire(generation)
    assert last.get() == ("second", "second")
    last.clear()


def test_cancel_before_injection_prevents_late_work():
    sessions = DictationSessions()
    first = sessions.start()
    assert sessions.queue(first)
    assert sessions.processing(first)
    assert sessions.cancel() == "cancelled"
    assert not sessions.begin_injection(first)
    assert not sessions.may_publish(first)
    second = sessions.start()
    assert second != first
    assert not sessions.queue(first)
    assert sessions.queue(second)


def test_injection_transition_is_atomic_and_too_late_is_reported():
    sessions = DictationSessions()
    current = sessions.start()
    assert sessions.queue(current)
    assert sessions.processing(current)
    assert sessions.begin_injection(current)
    assert sessions.cancel() == "too_late"
    assert sessions.may_publish(current)
    sessions.suppress_retention()
    assert not sessions.retention_allowed(current)
    sessions.finish(current)
    assert not sessions.may_publish(current)
