class OAuthHandler:
    def handle_callback(self, code: str) -> bool:
        return True if code else False
