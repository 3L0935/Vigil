from dictation_session import LastDictation


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
