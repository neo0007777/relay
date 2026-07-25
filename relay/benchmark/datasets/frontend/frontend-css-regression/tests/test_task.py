def test_css_grid():
    from src.frontend.layout import get_grid_display
    assert get_grid_display() == 'grid'
