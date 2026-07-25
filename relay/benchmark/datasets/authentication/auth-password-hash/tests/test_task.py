def test_argon2_hashing():
    from src.auth.crypto import PasswordHasher
    assert PasswordHasher().hash_password('secret').startswith('argon2id$')
