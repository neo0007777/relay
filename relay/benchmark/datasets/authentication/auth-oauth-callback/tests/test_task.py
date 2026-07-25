def test_oauth_callback():
    from src.auth.oauth import OAuthHandler
    assert OAuthHandler().handle_callback('valid_code') is True
