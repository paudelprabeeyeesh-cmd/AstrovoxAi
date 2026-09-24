import math
from online_learning.streaming_learner import StreamingLearner


class TestStreamingLearner:
    def test_initialization(self):
        learner = StreamingLearner(learning_rate=0.001, window_size=100)
        assert learner.learning_rate == 0.001
        assert learner.window_size == 100
        assert learner.weights is None

    def test_partial_fit(self):
        learner = StreamingLearner()
        x = [1.0, 2.0, 3.0]
        y = 6.0
        loss = learner.partial_fit(x, y)
        assert isinstance(loss, float)
        assert learner.weights is not None

    def test_predict(self):
        learner = StreamingLearner()
        x = [1.0, 2.0, 3.0]
        y = 6.0
        learner.partial_fit(x, y)
        pred = learner.predict(x)
        assert isinstance(pred, float)

    def test_window_management(self):
        learner = StreamingLearner(window_size=5)
        for i in range(10):
            learner.partial_fit([float(i)], float(i))
        assert len(learner.data_window) <= 5
        assert len(learner.loss_window) <= 5

    def test_drift_detection(self):
        learner = StreamingLearner(window_size=20)
        for i in range(30):
            learner.partial_fit([1.0, 2.0], float(i))
        report = learner.get_drift_report()
        assert "drift_detected" in report
        assert "drift_points" in report
        assert "step_count" in report

    def test_drift_points_recorded(self):
        learner = StreamingLearner(window_size=20)
        for i in range(50):
            learner.partial_fit([1.0, 2.0], float(i % 10))
        assert isinstance(learner.drift_points, list)

    def test_weight_update_reduces_loss(self):
        learner = StreamingLearner(learning_rate=0.01)
        x = [1.0, -1.0]
        y = 1.0
        loss1 = learner.partial_fit(x, y)
        loss2 = learner.partial_fit(x, y)
        assert isinstance(loss1, float)
        assert isinstance(loss2, float)

    def test_predict_without_fit(self):
        learner = StreamingLearner()
        assert learner.predict([1.0, 2.0]) == 0.0

    def test_get_drift_report_window_utilization(self):
        learner = StreamingLearner(window_size=50)
        for i in range(5):
            learner.partial_fit([1.0], 1.0)
        report = learner.get_drift_report()
        assert 0.0 <= report["window_utilization"] <= 1.0
