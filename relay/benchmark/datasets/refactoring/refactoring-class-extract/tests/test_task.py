def test_extracted_notification_service():
    from src.refactor.user import NotificationService
    assert NotificationService().send() == 'decoupled'
