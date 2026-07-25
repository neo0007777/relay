def test_fixture_teardown():
    from tests.fixtures import db_fixture
    assert db_fixture() == 'clean'
