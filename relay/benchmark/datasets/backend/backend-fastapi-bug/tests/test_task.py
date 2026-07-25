def test_fastapi_user_router():
    from src.backend.router import UserRouter
    assert UserRouter().get_user(42)['id'] == 42
