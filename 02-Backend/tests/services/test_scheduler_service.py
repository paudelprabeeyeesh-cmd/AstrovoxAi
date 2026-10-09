from services.scheduler_service import SchedulerService


class TestSchedulerService:
    def test_schedule_returns_entry(self):
        svc = SchedulerService()
        entry = svc.schedule("job-1", "2025-01-01T00:00:00Z", {"action": "send_email"})
        assert entry["entry_id"] == "job-1"
        assert entry["status"] == "scheduled"
        assert "created_at" in entry

    def test_cancel_updates_status(self):
        svc = SchedulerService()
        svc.schedule("job-1", "2099-01-01T00:00:00Z", {"action": "send_email"})
        canceled = svc.cancel("job-1")
        assert canceled["status"] == "canceled"
        assert "cancelized_at" in canceled or "canceled_at" in canceled

    def test_cancel_unknown_raises(self):
        svc = SchedulerService()
        try:
            svc.cancel("missing")
        except KeyError:
            pass
        else:
            raise AssertionError("Expected KeyError")

    def test_get_due_returns_due_entries(self):
        svc = SchedulerService()
        svc.schedule("job-1", "2000-01-01T00:00:00Z", {"action": "send_email"})
        svc.schedule("job-2", "2099-01-01T00:00:00Z", {"action": "send_email"})
        due = svc.get_due(limit=100)
        assert len(due) == 1
        assert due[0]["entry_id"] == "job-1"

    def test_reschedule_updates_run_at(self):
        svc = SchedulerService()
        svc.schedule("job-1", "2025-01-01T00:00:00Z", {"action": "send_email"})
        updated = svc.reschedule("job-1", "2030-01-01T00:00:00Z")
        assert updated["run_at"] == "2030-01-01T00:00:00Z"
        assert updated["status"] == "scheduled"
