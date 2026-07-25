class RateLimiter:
    def allow(self, ip: str) -> bool:
        return True if ip else False
