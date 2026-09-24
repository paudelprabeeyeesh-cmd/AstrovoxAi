
from complex_learning.online_meta_learning import OnlineMAML, FastAdaptationModel, Episode
import numpy as np


class TestOnlineMAML:
    def test_initialization(self):
        maml = OnlineMAML()
        assert maml.input_dim == 32
        assert maml.hidden_dim == 64
        assert maml.output_dim == 5
        assert len(maml.params) == 4

    def test_forward(self):
        maml = OnlineMAML(input_dim=8, hidden_dim=16, output_dim=3)
        x = np.random.randn(4, 8).astype(np.float64)
        logits = maml._forward(x, maml.params)
        assert logits.shape == (4, 3)

    def test_compute_loss(self):
        maml = OnlineMAML()
        logits = np.random.randn(4, 5).astype(np.float64)
        y = np.array([0, 1, 2, 3])
        loss = maml._compute_loss(logits, y)
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_adapt(self):
        maml = OnlineMAML(input_dim=8, hidden_dim=16, output_dim=3)
        np.random.seed(42)
        maml.params = {
            "W1": np.random.randn(8, 16).astype(np.float64) * 0.1,
            "b1": np.zeros(16, dtype=np.float64),
            "W2": np.random.randn(16, 3).astype(np.float64) * 0.1,
            "b2": np.zeros(3, dtype=np.float64),
        }
        x = np.random.randn(4, 8).astype(np.float64)
        y = np.array([0, 1, 2, 0])
        adapted = maml.adapt(x, y, steps=3)
        assert set(adapted.keys()) == set(maml.params.keys())
        assert adapted["W1"].shape == maml.params["W1"].shape

    def test_meta_train_step(self):
        np.random.seed(42)
        maml = OnlineMAML(input_dim=8, hidden_dim=16, output_dim=3, num_tasks=4, num_query=2)
        tasks = []
        for i in range(4):
            supp_x = np.random.randn(2, 8).astype(np.float64)
            supp_y = np.array([i % 3, (i + 1) % 3])
            q_x = np.random.randn(2, 8).astype(np.float64)
            q_y = np.array([i % 3, (i + 1) % 3])
            tasks.append(Episode(supp_x, supp_y, q_x, q_y, n_way=3, k_shot=1))
        loss = maml.meta_train_step(tasks)
        assert isinstance(loss, float)
        assert loss >= 0.0
        assert len(maml.task_losses) == 1

    def test_online_step(self):
        maml = OnlineMAML(input_dim=8, hidden_dim=16, output_dim=3)
        np.random.seed(42)
        maml.params = {
            "W1": np.random.randn(8, 16).astype(np.float64) * 0.1,
            "b1": np.zeros(16, dtype=np.float64),
            "W2": np.random.randn(16, 3).astype(np.float64) * 0.1,
            "b2": np.zeros(3, dtype=np.float64),
        }
        x = np.random.randn(4, 8).astype(np.float64)
        y = np.array([0, 1, 2, 0])
        loss = maml.online_step(x, y)
        assert isinstance(loss, float)
        assert len(maml.step_losses) == 1

    def test_evaluate_episode(self):
        maml = OnlineMAML(input_dim=8, hidden_dim=16, output_dim=3)
        np.random.seed(42)
        maml.params = {
            "W1": np.random.randn(8, 16).astype(np.float64) * 0.1,
            "b1": np.zeros(16, dtype=np.float64),
            "W2": np.random.randn(16, 3).astype(np.float64) * 0.1,
            "b2": np.zeros(3, dtype=np.float64),
        }
        ep = Episode(
            np.random.randn(4, 8).astype(np.float64),
            np.array([0, 1, 2, 0]),
            np.random.randn(4, 8).astype(np.float64),
            np.array([0, 1, 2, 0]),
            n_way=3, k_shot=1,
        )
        result = maml.evaluate_episode(ep)
        assert "loss" in result
        assert "accuracy" in result
        assert "predictions" in result
        assert result["predictions"].shape == (4,)

    def test_get_training_report(self):
        maml = OnlineMAML()
        report = maml.get_training_report()
        assert "num_meta_steps" in report
        assert "num_online_steps" in report


class TestFastAdaptationModel:
    def test_initialization(self):
        fam = FastAdaptationModel()
        assert fam.input_dim == 32
        assert fam.hidden_dim == 64
        assert fam.num_classes == 5

    def test_adapt(self):
        fam = FastAdaptationModel(input_dim=8, hidden_dim=16, num_classes=3)
        np.random.seed(42)
        fam.params = {
            "W1": np.random.randn(8, 16).astype(np.float64) * 0.1,
            "b1": np.zeros(16, dtype=np.float64),
            "W2": np.random.randn(16, 3).astype(np.float64) * 0.1,
            "b2": np.zeros(3, dtype=np.float64),
        }
        x = np.random.randn(4, 8).astype(np.float64)
        y = np.array([0, 1, 2, 0])
        adapted = fam.adapt(x, y)
        assert len(fam.loss_history) == 10

    def test_predict(self):
        fam = FastAdaptationModel(input_dim=8, hidden_dim=16, num_classes=3)
        np.random.seed(42)
        fam.params = {
            "W1": np.random.randn(8, 16).astype(np.float64) * 0.1,
            "b1": np.zeros(16, dtype=np.float64),
            "W2": np.random.randn(16, 3).astype(np.float64) * 0.1,
            "b2": np.zeros(3, dtype=np.float64),
        }
        x = np.random.randn(4, 8).astype(np.float64)
        preds = fam.predict(x)
        assert preds.shape == (4,)
        assert all(p in [0, 1, 2] for p in preds)

    def test_get_adaptation_report(self):
        fam = FastAdaptationModel()
        report = fam.get_adaptation_report()
        assert "steps" in report
        assert "final_loss" in report
