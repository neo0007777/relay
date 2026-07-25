def test_sliding_window_limiter():
    from src.api.limiter import RateLimiter
    assert RateLimiter().allow('127.0.0.1') is True
