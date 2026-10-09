from world_model.environment_model import EnvironmentState, StateObserver


class TestStateObserver:
    def test_record_appends_history(self):
        observer = StateObserver()
        snapshot = observer.record([1.0, 2.0])
        assert len(observer.get_history()) == 1
        assert isinstance(snapshot, EnvironmentState)
        assert snapshot.time_step == 0
        assert snapshot.entities["env"] == [1.0, 2.0]

    def test_get_history_returns_copy(self):
        observer = StateObserver()
        observer.record([0.0])
        history = observer.get_history()
        assert history is not observer.history
        assert len(history) == 1
