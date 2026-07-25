def test_stripe_integration():
    from src.payments.stripe import StripeHandler
    assert StripeHandler().process({'amount': 100}) is True
