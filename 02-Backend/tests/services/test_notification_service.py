from services.notification_service import NotificationService


class TestNotificationService:
    def test_send_email_returns_entry(self):
        svc = NotificationService()
        entry = svc.send_email("user@example.com", "Hello", "Body")
        assert entry["type"] == "email"
        assert entry["recipient"] == "user@example.com"
        assert "timestamp" in entry

    def test_send_in_app_stores_notification(self):
        svc = NotificationService()
        entry = svc.send_in_app("user-1", "Hello world")
        assert entry["type"] == "in_app"
        assert entry["user_id"] == "user-1"
        notifications = svc.get_notifications("user-1")
        assert len(notifications) == 1
        assert notifications[0]["message"] == "Hello world"

    def test_get_notifications_empty(self):
        svc = NotificationService()
        assert svc.get_notifications("unknown") == []

    def test_get_notifications_limit(self):
        svc = NotificationService()
        for i in range(5):
            svc.send_in_app("user-1", f"msg {i}")
        assert len(svc.get_notifications("user-1", limit=3)) == 3
