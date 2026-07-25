def test_fd_closed():
    from src.memory.reader import StreamReader
    assert StreamReader().read_all() == 'closed'
