def test_mocked_fetch():
    from src.client.http import APIClient
    assert APIClient().fetch() == 'mocked'
