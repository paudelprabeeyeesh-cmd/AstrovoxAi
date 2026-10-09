

from inference_engine.continuous_batching import (
    ContinuousBatchScheduler, ScheduledRequest
)


def test_continuous_batch_scheduler_submit():
    scheduler = ContinuousBatchScheduler(max_active=2, max_queue=4, max_preempted=1)
    req = ScheduledRequest(request_id="r1", prompt_ids=[1, 2, 3], max_new_tokens=10)
    scheduler.submit(req)
    assert "r1" in scheduler.active


def test_continuous_batch_scheduler_full():
    scheduler = ContinuousBatchScheduler(max_active=1, max_queue=1, max_preempted=1)
    scheduler.submit(ScheduledRequest(request_id="r1", prompt_ids=[1], max_new_tokens=5))
    scheduler.submit(ScheduledRequest(request_id="r2", prompt_ids=[2], max_new_tokens=5))
    stats = scheduler.get_stats()
    assert stats["active"] == 1
    assert stats["queued"] == 1


def test_continuous_batch_scheduler_preempt():
    scheduler = ContinuousBatchScheduler(max_active=1, max_queue=0, max_preempted=1)
    scheduler.submit(ScheduledRequest(request_id="r1", prompt_ids=[1], max_new_tokens=5, priority=0))
    scheduler.submit(ScheduledRequest(request_id="r2", prompt_ids=[2], max_new_tokens=5, priority=1))
    assert "r2" in scheduler.active
    assert "r1" in scheduler.preempted


def test_scheduler_completion_promotes_queued():
    scheduler = ContinuousBatchScheduler(max_active=1, max_queue=1, max_preempted=0)
    r1 = ScheduledRequest(request_id="r1", prompt_ids=[1], max_new_tokens=1)
    r2 = ScheduledRequest(request_id="r2", prompt_ids=[2], max_new_tokens=5)
    scheduler.submit(r1)
    scheduler.submit(r2)
    assert r2.state.value == "waiting"
    scheduler.step()
    assert "r1" in scheduler.completed
    assert "r2" in scheduler.active


def test_scheduler_reject_on_full_queue():
    scheduler = ContinuousBatchScheduler(max_active=1, max_queue=1, max_preempted=0)
    scheduler.submit(ScheduledRequest(request_id="r1", prompt_ids=[1], max_new_tokens=5))
    scheduler.submit(ScheduledRequest(request_id="r2", prompt_ids=[2], max_new_tokens=5))
    result = scheduler.submit(ScheduledRequest(request_id="r3", prompt_ids=[3], max_new_tokens=5))
    assert result is False
    assert "r3" in scheduler.rejected


def test_scheduler_resume_preempted():
    scheduler = ContinuousBatchScheduler(max_active=1, max_queue=0, max_preempted=1)
    scheduler.submit(ScheduledRequest(request_id="r1", prompt_ids=[1], max_new_tokens=5, priority=0))
    scheduler.submit(ScheduledRequest(request_id="r2", prompt_ids=[2], max_new_tokens=5, priority=1))
    assert "r1" in scheduler.preempted
    assert scheduler.resume("r1") is True
    assert "r1" in scheduler.active


def test_scheduler_stats():
    scheduler = ContinuousBatchScheduler(max_active=2, max_queue=2, max_preempted=1)
    scheduler.submit(ScheduledRequest(request_id="r1", prompt_ids=[1], max_new_tokens=1))
    scheduler.submit(ScheduledRequest(request_id="r2", prompt_ids=[2], max_new_tokens=1))
    stats = scheduler.get_stats()
    assert stats["active"] == 2
    assert stats["queued"] == 0
    assert stats["completed"] == 0
    assert stats["preempted"] == 0


def test_request_total_tokens():
    req = ScheduledRequest(request_id="r1", prompt_ids=[1, 2, 3], max_new_tokens=5)
    req.generated_tokens = [10, 20]
    assert req.total_tokens == 5
