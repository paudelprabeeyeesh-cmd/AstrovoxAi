from final_system.rollback_controller import RollbackController, RollbackRecord, RollbackStatus


def test_initiate_rollback():
    controller = RollbackController()
    record = controller.initiate("0.9.0", steps=["restore_db", "restart"])
    assert record.target_version == "0.9.0"
    assert record.status == RollbackStatus.PENDING
    assert record.steps == ["restore_db", "restart"]


def test_execute_rollback():
    controller = RollbackController()
    record = controller.initiate("0.9.0", steps=["step1"])
    executed = []

    def runner(step):
        executed.append(step)

    updated = controller.execute(record, runner)
    assert updated.status == RollbackStatus.COMPLETED
    assert executed == ["step1"]
    assert updated.started_at is not None
    assert updated.finished_at is not None


def test_execute_rollback_failure():
    controller = RollbackController()
    record = controller.initiate("0.9.0", steps=["step1", "step2"])

    def runner(step):
        if step == "step1":
            raise RuntimeError("fail")

    updated = controller.execute(record, runner)
    assert updated.status == RollbackStatus.FAILED
    assert updated.error == "fail"


def test_history():
    controller = RollbackController()
    controller.initiate("0.9.0")
    controller.initiate("0.8.0")
    history = controller.history()
    assert len(history) == 2
    assert history[0].target_version == "0.9.0"
    assert history[1].target_version == "0.8.0"
