def test_threadpool_shutdown():
    from src.concurrency.pool import ThreadPool
    assert ThreadPool().shutdown() is True
