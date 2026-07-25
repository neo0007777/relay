def test_dfs_cycle_prevention():
    from src.debug.graph import GraphDFS
    assert GraphDFS().traverse() is True
