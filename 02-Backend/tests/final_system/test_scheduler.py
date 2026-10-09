import pytest
from final_system.scheduler import ScheduledJob, Scheduler


def test_schedule_and_run_job():
    scheduler = Scheduler()
    scheduler.schedule(ScheduledJob(name="j1", cron="* * * * *", fn=lambda: 42))
    result = scheduler.run_job("j1")
    assert result == 42


def test_cancel_job():
    scheduler = Scheduler()
    scheduler.schedule(ScheduledJob(name="j1", cron="* * * * *", fn=lambda: None))
    scheduler.cancel("j1")
    with pytest.raises(KeyError):
        scheduler.run_job("j1")


def test_list_jobs():
    scheduler = Scheduler()
    scheduler.schedule(ScheduledJob(name="a", cron="* * * * *", fn=lambda: None))
    scheduler.schedule(ScheduledJob(name="b", cron="* * * * *", fn=lambda: None))
    assert set(scheduler.list_jobs()) == {"a", "b"}


def test_start_stop():
    scheduler = Scheduler()
    scheduler.schedule(ScheduledJob(name="j", cron="* * * * *", fn=lambda: None))
    scheduler.start()
    assert scheduler._running is True
    scheduler.stop()
    assert scheduler._running is False


def test_missing_job():
    scheduler = Scheduler()
    with pytest.raises(KeyError):
        scheduler.run_job("missing")
