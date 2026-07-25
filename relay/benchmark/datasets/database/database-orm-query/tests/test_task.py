def test_query_count():
    from src.db.queries import QueryOptimizer
    assert QueryOptimizer().fetch_users() == 1 # 1 join query
