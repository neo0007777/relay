def test_type_annotations():
    from src.refactor.types import process_user
    assert process_user('alice') == 'ALICE'
