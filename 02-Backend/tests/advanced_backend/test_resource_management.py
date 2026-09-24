from advanced_backend.resource_management import CPUScheduler, Quota, ResourceManager


def test_resource_manager_consume_allowed():
    rm = ResourceManager()
    rm.set_limit("svc", Quota(requests=5))
    assert rm.consume("svc", Quota(requests=1)) is True


def test_resource_manager_consume_denied():
    rm = ResourceManager()
    rm.set_limit("svc", Quota(requests=1))
    assert rm.consume("svc", Quota(requests=1)) is True
    assert rm.consume("svc", Quota(requests=1)) is False


def test_resource_manager_reset():
    rm = ResourceManager()
    rm.set_limit("svc", Quota(requests=1))
    rm.consume("svc", Quota(requests=1))
    rm.reset("svc")
    assert rm.consume("svc", Quota(requests=1)) is True


def test_cpu_scheduler_rounds():
    sched = CPUScheduler(cores=2)
    sched.schedule("a", 0.25)
    sched.schedule("b", 0.25)
    assert sched.tick(quantum=0.1) == "a"
    assert sched.tick(quantum=0.1) == "b"


def test_report():
    rm = ResourceManager()
    rm.set_quota("x", Quota(cpu_seconds=1.0))
    rep = rm.report()
    assert rep["x"]["cpu_seconds"] == 1.0
