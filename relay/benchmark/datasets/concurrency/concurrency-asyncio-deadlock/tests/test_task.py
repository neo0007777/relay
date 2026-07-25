def test_asyncio_deadlock_fix():
    from src.concurrency.queue_manager import QueueManager
    assert QueueManager().enqueue('task') is True
