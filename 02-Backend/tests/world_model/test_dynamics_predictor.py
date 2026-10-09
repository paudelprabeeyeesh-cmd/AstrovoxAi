import unittest

from world_model.environment_model import EnvironmentModel


class TestEnvironmentModel(unittest.TestCase):
    def test_init(self):
        model = EnvironmentModel(state_dim=4, action_dim=2)
        self.assertEqual(model.state_dim, 4)
        self.assertEqual(model.state, [0.0, 0.0, 0.0, 0.0])
        self.assertEqual(model.observer.history, [])

    def test_set_state(self):
        model = EnvironmentModel(state_dim=2)
        model.set_state([1.0, 2.0])
        self.assertEqual(model.state, [1.0, 2.0])
        self.assertEqual(len(model.observer.history), 1)

    def test_step_no_action(self):
        model = EnvironmentModel(state_dim=2, action_dim=2)
        model.set_state([0.0, 0.0])
        next_state = model.step()
        self.assertEqual(len(next_state), 2)

    def test_step_with_action(self):
        model = EnvironmentModel(state_dim=2, action_dim=2)
        model.set_state([0.0, 0.0])
        next_state = model.step(action=[0.1, 0.2])
        self.assertEqual(len(next_state), 2)

    def test_history(self):
        model = EnvironmentModel(state_dim=2)
        model.step()
        model.step()
        self.assertEqual(len(model.observer.history), 2)

    def test_predict(self):
        model = EnvironmentModel(state_dim=2)
        model.set_state([0.0, 0.0])
        predictions = model.predict(horizon=3, actions=[[0.0, 0.0]] * 3)
        self.assertEqual(len(predictions), 4)

    def test_predict_default_actions(self):
        model = EnvironmentModel(state_dim=2)
        model.set_state([0.0, 0.0])
        predictions = model.predict(horizon=2)
        self.assertEqual(len(predictions), 3)

    def test_learn_transition(self):
        model = EnvironmentModel(state_dim=2)
        model.learn_transition([0.0, 0.0], [0.0, 0.0], [0.1, 0.1])
        self.assertEqual(len(model.learned_transitions), 1)

    def test_dynamics_uncertainty(self):
        model = EnvironmentModel(state_dim=4)
        uncertainty = model.dynamics_uncertainty()
        self.assertIsInstance(uncertainty, float)

    def test_learn_transition_updates_noise(self):
        model = EnvironmentModel(state_dim=2)
        model.learn_transition([0.0, 0.0], [0.0, 0.0], [0.1, 0.1])
        model.learn_transition([0.1, 0.1], [0.0, 0.0], [0.2, 0.2])
        self.assertEqual(len(model.dynamics.noise_covariance), 2)

    def test_predict_shape(self):
        model = EnvironmentModel(state_dim=3)
        model.set_state([0.0, 0.0, 0.0])
        preds = model.predict(horizon=5)
        self.assertEqual(len(preds), 6)
        self.assertEqual(len(preds[0]), 3)


if __name__ == "__main__":
    unittest.main()
