import unittest

from world_model.environment_model import DynamicsModel, TransitionModel


class TestDynamicsModel(unittest.TestCase):
    def test_defaults(self):
        m = DynamicsModel()
        self.assertEqual(m.transition_matrix, [])
        self.assertEqual(m.noise_covariance, [])


class TestTransitionModel(unittest.TestCase):
    def test_defaults(self):
        m = TransitionModel(state_dim=4)
        self.assertEqual(m.state_dim, 4)
        self.assertEqual(len(m.transition_matrix), 4)
        self.assertEqual(len(m.transition_matrix[0]), 4)

    def test_step(self):
        m = TransitionModel(state_dim=2)
        result = m.step([0.0, 0.0], [0.0, 0.0])
        self.assertEqual(len(result), 2)

    def test_step_with_action(self):
        m = TransitionModel(state_dim=2)
        result = m.step([1.0, 2.0], [0.1, 0.2])
        self.assertEqual(len(result), 2)

    def test_matmul(self):
        m = TransitionModel(state_dim=2)
        matrix = [[1.0, 0.0], [0.0, 1.0]]
        vector = [3.0, 4.0]
        result = m._matmul(matrix, vector)
        self.assertEqual(result, [3.0, 4.0])

    def test_matmul_2x3(self):
        m = TransitionModel(state_dim=2)
        matrix = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        vector = [1.0, 2.0, 3.0]
        result = m._matmul(matrix, vector)
        self.assertEqual(result, [14.0, 32.0])

    def test_update_records_transition(self):
        m = TransitionModel(state_dim=2)
        m.update([0.0, 0.0], [0.0, 0.0], [0.1, 0.1])
        self.assertEqual(len(m.learned_transitions), 1)
        m.update([0.1, 0.1], [0.0, 0.0], [0.2, 0.2])
        self.assertEqual(len(m.learned_transitions), 2)

    def test_update_changes_noise(self):
        m = TransitionModel(state_dim=2)
        m.update([0.0, 0.0], [0.0, 0.0], [0.1, 0.1])
        m.update([0.1, 0.1], [0.0, 0.0], [0.2, 0.2])
        self.assertEqual(len(m.noise_covariance), 2)
        self.assertEqual(len(m.noise_covariance[0]), 2)


if __name__ == "__main__":
    unittest.main()
