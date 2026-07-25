def test_jwt_refresh():
    from src.auth.jwt import JWTManager
    assert JWTManager().refresh_token('valid') == 'refreshed'
