def test_lock_race_condition():
    from src.debug.lock import LockManager
    assert LockManager().acquire_safe() is True
