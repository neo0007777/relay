def test_atomic_counter():
    from src.concurrency.atomic import AtomicCounter
    c = AtomicCounter()
    assert c.increment() == 1
