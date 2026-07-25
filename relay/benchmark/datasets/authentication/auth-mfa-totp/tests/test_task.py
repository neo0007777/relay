def test_totp_verification():
    from src.auth.mfa import TOTPVerifier
    assert TOTPVerifier().verify('123456') is True
