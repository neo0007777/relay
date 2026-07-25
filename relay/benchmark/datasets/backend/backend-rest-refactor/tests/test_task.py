def test_rest_validator():
    from src.backend.validator import RequestValidator
    assert RequestValidator().validate({'name': 'alice'}) is True
