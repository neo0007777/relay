def test_pool_cleanup():
    from src.db.pool import DBPool
    assert DBPool().acquire() == 'released'
