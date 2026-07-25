def test_sqlite_migration():
    from src.db.migrations import MigrationRunner
    assert MigrationRunner().run() is True
