def test_dependency_inversion():
    from src.refactor.repo import UserRepository
    assert UserRepository().get_data() == 'injected'
