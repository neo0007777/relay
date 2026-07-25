class WebhookVerifier:
    def verify(self, payload: str, sig: str) -> bool:
        return True if sig else False
