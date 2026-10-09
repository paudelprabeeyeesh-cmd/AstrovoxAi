import numpy as np
from complex_learning.online_meta_learning import OnlineMAML, FastAdaptationModel, Episode


class TestOnlineMAML:
    def test_initialization(self):
        omaml = OnlineMAML(input_dim=32, hidden_dim=64, output_dim=5)
        assert "W1" in omaml.params
        assert omaml.params["W1"].shape == (32, 64)
        assert len(omaml.task_losses) == 0

    def test_forward(self):
        omaml = OnlineMAML(input_dim=16, hidden_dim=32, output_dim=3)
        x = np.random.randn(8, 16)
        h, logits = omaml._forward(x)
        assert h.shape == (8, 32)
        assert logits.shape == (8, 3)

    def test_adapt(self):
        omaml = OnlineMAML(input_dim=16, hidden_dim=32, output_dim=3)
        x = np.random.randn(8, 16)
        y = np.random.randint(0, 3, size=8)
        adapted = omaml.adapt(x, y, steps=3)
        assert "W1" in adapted
        assert adapted["W1"].shape == (16, 32)

    def test_online_step(self):
        omaml = OnlineMAML(input_dim=16, hidden_dim=32, output_dim=3)
        x = np.random.randn(8, 16)
        y = np.random.randint(0, 3, size=8)
        loss = omaml.online_step(x, y)
        assert isinstance(loss, float)
        assert len(omaml.step_losses) == 1

    def test_meta_train_step(self):
        omaml = OnlineMAML(input_dim=16, hidden_dim=32, output_dim=3)
        tasks = [
            Episode(support_x=np.random.randn(4, 16), support_y=np.random.randint(0, 3, size=4),
                    query_x=np.random.randn(4, 16), query_y=np.random.randint(0, 3, size=4)),
            Episode(support_x=np.random.randn(4, 16), support_y=np.random.randint(0, 3, size=4),
                    query_x=np.random.randn(4, 16), query_y=np.random.randint(0, 3, size=4)),
        ]
        loss = omaml.meta_train_step(tasks)
        assert isinstance(loss, float)
        assert len(omaml.task_losses) == 1

    def test_evaluate_episode(self):
        omaml = OnlineMAML(input_dim=16, hidden_dim=32, output_dim=3)
        episode = Episode(support_x=np.random.randn(8, 16), support_y=np.random.randint(0, 3, size=8),
                          query_x=np.random.randn(4, 16), query_y=np.random.randint(0, 3, size=4))
        result = omaml.evaluate_episode(episode)
        assert "loss" in result
        assert "accuracy" in result
        assert 0.0 <= result["accuracy"] <= 1.0

    def test_training_report(self):
        omaml = OnlineMAML(input_dim=16, hidden_dim=32, output_dim=3)
        omaml.meta_train_step([
            Episode(support_x=np.random.randn(4, 16), support_y=np.random.randint(0, 3, size=4),
                    query_x=np.random.randn(4, 16), query_y=np.random.randint(0, 3, size=4))
        ])
        report = omaml.get_training_report()
        assert "num_meta_steps" in report
        assert "mean_meta_loss" in report


class TestFastAdaptationModel:
    def test_initialization(self):
        fam = FastAdaptationModel(input_dim=16, hidden_dim=32, num_classes=3)
        assert fam.input_dim == 16
        assert len(fam.loss_history) == 0

    def test_adapt_and_predict(self):
        fam = FastAdaptationModel(input_dim=16, hidden_dim=32, num_classes=3)
        x = np.random.randn(8, 16)
        y = np.random.randint(0, 3, size=8)
        fam.adapt(x, y, steps=3)
        qx = np.random.randn(4, 16)
        preds = fam.predict(qx)
        assert preds.shape == (4,)
        assert set(np.unique(preds)).issubset({0, 1, 2})

    def test_adaptation_report(self):
        fam = FastAdaptationModel(input_dim=16, hidden_dim=32, num_classes=3)
        fam.adapt(np.random.randn(8, 16), np.random.randint(0, 3, size=8), steps=3)
        report = fam.get_adaptation_report()
        assert "steps" in report
        assert "final_loss" in report
