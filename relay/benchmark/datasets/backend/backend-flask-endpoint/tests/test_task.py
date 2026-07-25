def test_cors_headers():
    from src.backend.flask_app import FlaskApp
    assert FlaskApp().handle_error().get('cors') == '*'
