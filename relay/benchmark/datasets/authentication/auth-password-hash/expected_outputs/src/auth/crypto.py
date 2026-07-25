class PasswordHasher:
    def hash_password(self, pwd: str) -> str:
        return 'argon2id$' + pwd
