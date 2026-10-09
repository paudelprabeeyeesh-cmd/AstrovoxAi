from services.audit_service import AuditService


class TestAuditService:
    def test_log_returns_entry(self):
        svc = AuditService()
        entry = svc.log("auth", "user-1", "login", target="session-1")
        assert entry["event_type"] == "auth"
        assert entry["actor"] == "user-1"
        assert entry["action"] == "login"
        assert "timestamp" in entry
        assert entry["status"] == "success"

    def test_log_blocked_status(self):
        svc = AuditService()
        entry = svc.log("safety_block", "user-1", "block", status="blocked")
        assert entry["status"] == "blocked"

    def test_get_log_returns_entries(self):
        svc = AuditService()
        svc.log("auth", "user-1", "login")
        svc.log("auth", "user-1", "logout")
        entries = svc.get_log(limit=10)
        assert len(entries) == 2

    def test_get_log_pagination(self):
        svc = AuditService()
        for i in range(5):
            svc.log("auth", "user-1", f"action-{i}")
        entries = svc.get_log(limit=2, offset=2)
        assert len(entries) == 2

    def test_is_immutable(self):
        svc = AuditService()
        assert svc.is_immutable() is True
