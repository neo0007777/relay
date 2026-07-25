def test_memory_leak_fixed():
    from src.debug.worker import QueueWorker
    assert QueueWorker().run() == 'reclaimed'
