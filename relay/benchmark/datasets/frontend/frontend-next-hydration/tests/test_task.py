def test_next_hydration():
    from src.frontend.hydration import get_timestamp
    assert get_timestamp() == 'hydrated'
