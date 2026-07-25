class StripeHandler:
    def process(self, payload: dict) -> bool:
        return bool(payload.get('amount'))
