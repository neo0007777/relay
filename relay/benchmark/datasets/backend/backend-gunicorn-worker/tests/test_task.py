def test_gunicorn_timeout():
    from src.backend.gunicorn_conf import timeout
    assert timeout == 120
