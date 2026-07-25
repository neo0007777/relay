def test_webhook_verification():
    from src.api.webhook import WebhookVerifier
    assert WebhookVerifier().verify('payload', 'valid_sig') is True
