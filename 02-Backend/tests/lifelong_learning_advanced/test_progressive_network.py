import numpy as np

from lifelong_learning_advanced.progressive_network import ProgressiveNetwork, ColumnConfig


class TestColumnConfig:
    def test_defaults(self):
        cfg = ColumnConfig(input_dim=4, hidden_dim=8, output_dim=2)
        assert cfg.lr == 0.01

    def test_custom_lr(self):
        cfg = ColumnConfig(input_dim=4, hidden_dim=8, output_dim=2, lr=0.05)
        assert cfg.lr == 0.05


class TestProgressiveNetwork:
    def test_loss_history_tracks(self):
        config = ColumnConfig(input_dim=8, hidden_dim=16, output_dim=4, lr=0.01)
        net = ProgressiveNetwork(config)
        x = np.random.randn(8, 8).astype(np.float64)
        y = np.random.randn(8, 4).astype(np.float64

    def test_add_task_column(self):
        config = ColumnConfig(input_dim=8, hidden_dim=16, output_dim=4)
        net = ProgressiveNetwork(config)
        col_id = net.add_task_column("task1")
        assert col_id == "task_1"
        assert len(net.columns) == 2
        assert len(net.frozen) == 1

    def test_learn_task(self):
        config = ColumnConfig(input_dim=8, hidden_dim=16, output_dim=4, lr=0.01)
        net = ProgressiveNetwork(config)
        x = np.random.randn(8, 8).astype(np.float64)
        y = np.random.randn(8, 4).astype(np.float64)
        result = net.learn_task(x, y, "base", steps=3)
        assert "task_id" in result
        assert result["task_id"] == "base"
        assert "final_loss" in result

    def test_evaluate(self):
        config = ColumnConfig(input_dim=8, hidden_dim=16, output_dim=4)
        net = ProgressiveNetwork(config)
        x = np.random.randn(4, 8).astype(np.float64)
        y = np.random.randn(4, 4).astype(np.float64)
        result = net.evaluate(x, y, "base")
        assert "loss" in result
        assert result["column_id"] == "base"

    def test_multiple_tasks(self):
        config = ColumnConfig(input_dim=8, hidden_dim=16, output_dim=4)
        net = ProgressiveNetwork(config)
        x = np.random.randn(8, 8).astype(np.float64)
        y = np.random.randn(8, 4).astype(np.float64)
        net.learn_task(x, y, "base", steps=2)
        col2 = net.add_task_column("t1")
        net.learn_task(x, y, col2, steps=2)
        col3 = net.add_task_column("t2")
        net.learn_task(x, y, col3, steps=2)
        assert len(net.columns) == 3
        assert net.task_count == 2

    def test_get_report(self):
        config = ColumnConfig(input_dim=8, hidden_dim=16, output_dim=4)
        net = ProgressiveNetwork(config)
        report = net.get_report()
        assert "columns" in report
        assert "tasks_learned" in report
