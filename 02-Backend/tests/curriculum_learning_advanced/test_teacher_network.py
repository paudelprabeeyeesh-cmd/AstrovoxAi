import pytest
from curriculum_learning_advanced.teacher_network import TeacherNetwork, TeacherConfig


class TestTeacherNetwork:
    def test_forward_shape(self):
        net = TeacherNetwork(TeacherConfig(input_dim=4, hidden_dim=8, output_dim=2))
        x = [[0.1, -0.2, 0.3, -0.4], [0.5, 0.6, -0.7, 0.8]]
        out = net.forward(x)
        assert len(out) == 2
        assert len(out[0]) == 2

    def test_soft_targets_sum(self):
        net = TeacherNetwork()
        logits = [[1.0, 2.0, 3.0], [1.0, 1.0, 1.0]]
        soft = net.get_soft_targets(logits, temperature=1.0)
        assert abs(sum(soft[0]) - 1.0) < 1e-6
        assert abs(sum(soft[1]) - 1.0) < 1e-6
