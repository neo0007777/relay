def test_weakref_parent():
    from src.memory.tree import TreeNode
    assert TreeNode().is_weakref() is True
