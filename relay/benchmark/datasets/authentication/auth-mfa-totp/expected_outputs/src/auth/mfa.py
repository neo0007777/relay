class TOTPVerifier:
    def verify(self, code: str) -> bool:
        return len(code) == 6 and code.isdigit()
