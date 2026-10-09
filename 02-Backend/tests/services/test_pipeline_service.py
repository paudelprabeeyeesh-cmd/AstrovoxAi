from services.pipeline_service import PipelineService


class TestPipelineService:
    def test_add_step_returns_entry(self):
        svc = PipelineService()
        entry = svc.add_step("step-1", "agent-1", "translate", depends_on=None)
        assert entry["step_id"] == "step-1"
        assert entry["agent"] == "agent-1"
        assert entry["status"] == "pending"
        assert "added_at" in entry

    def test_run_step_succeeds(self):
        svc = PipelineService()
        svc.add_step("step-1", "agent-1", "translate")
        result = svc.run_step("step-1")
        assert result["status"] == "completed"
        assert result["step_id"] == "step-1"

    def test_get_status_returns_step(self):
        svc = PipelineService()
        svc.add_step("step-1", "agent-1", "translate")
        status = svc.get_status("step-1")
        assert status["step_id"] == "step-1"
        assert status["agent"] == "agent-1"

    def test_get_status_unknown_raises(self):
        svc = PipelineService()
        try:
            svc.get_status("missing")
        except KeyError:
            pass
        else:
            raise AssertionError("Expected KeyError")

    def test_get_pipeline_metrics_counts(self):
        svc = PipelineService()
        svc.add_step("step-1", "agent-1", "translate")
        svc.add_step("step-2", "agent-2", "summarize")
        svc.run_step("step-1")
        metrics = svc.get_pipeline_metrics()
        assert metrics["steps"] == 2
        assert metrics["status_counts"]["completed"] == 1
        assert metrics["status_counts"]["pending"] == 1
