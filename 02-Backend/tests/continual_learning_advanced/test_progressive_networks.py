import math
import pytest
from continual_learning_advanced.progressive_networks import ProgressiveNetwork


class TestProgressiveNetwork:
    def test_initialization(self):
        pn = ProgressiveNetwork(max_columns=3)
        assert pn.max_columns == 3
        assert pn.column_count == 0
        assert pn.task_to_column == {}

    def test_add_column(self):
        pn = ProgressiveNetwork()
        col_id = pn.add_column(task_id=1, input_dim=4, hidden_dim=8, output_dim=2)
        assert col_id == 0
        assert 1 in pn.task_to_column
        assert pn.task_to_column[1] == 0

    def test_add_column_max_reached(self):
        pn = ProgressiveNetwork(max_columns=1)
        pn.add_column(task_id=1, input_dim=2, hidden_dim=2, output_dim=2)
        with pytest.raises(ValueError, match="Maximum columns reached"):
            pn.add_column(task_id=2, input_dim=2, hidden_dim=2, output_dim=2)

    def test_forward(self):
        pn = ProgressiveNetwork()
        pn.add_column(task_id=1, input_dim=2, hidden_dim=2, output_dim=2)
        out = pn.forward(1, [1.0, 0.0])
        assert len(out) == 2

    def test_forward_second_column_uses_lateral(self):
        pn = ProgressiveNetwork()
        pn.add_column(task_id=1, input_dim=2, hidden_dim=2, output_dim=2)
        pn.add_column(task_id=2, input_dim=2, hidden_dim=2, output_dim=2)
        out = pn.forward(2, [1.0, 0.0])
        assert len(out) == 2

    def test_train_step(self):
        pn = ProgressiveNetwork()
        pn.add_column(task_id=1, input_dim=2, hidden_dim=2, output_dim=2)
        loss = pn.train_step(1, [1.0, 0.0], [0.5, -0.5], lr=0.01)
        assert loss >= 0.0
        assert len(pn.loss_history[1]) == 1

    def test_get_column_params(self):
        pn = ProgressiveNetwork()
        pn.add_column(task_id=1, input_dim=2, hidden_dim=2, output_dim=2)
        params = pn.get_column_params(1)
        assert "W1" in params
        assert "b1" in params
        assert len(params["W1"]) == 4

    def test_column_summary(self):
        pn = ProgressiveNetwork()
        pn.add_column(task_id=1, input_dim=2, hidden_dim=4, output_dim=3)
        summary = pn.column_summary()
        assert 0 in summary
        assert summary[0]["input_dim"] == 2
        assert summary[0]["hidden_dim"] == 4
        assert summary[0]["output_dim"] == 3
        assert summary[0]["task_id"] == 1
