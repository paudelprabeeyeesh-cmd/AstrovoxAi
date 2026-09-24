import numpy as np
from world_model.environment_model import EnvironmentModel


class TestEnvironmentModel:
    def test_step_changes_state(self):
        env = EnvironmentModel(state_dim=2)
        env.set_state(np.array([1.0, 0.0]))
        new_state = env.step()
        assert new_state.shape == (2,)
        assert len(env.history) == 2

    def test_predict_horizon(self):
        env = EnvironmentModel(state_dim=2)
        env.set_state(np.array([1.0, 0.0]))
        predictions = env.predict(horizon=3)
        assert predictions.shape == (4, 2)

    def test_learn_transition_updates_noise(self):
        env = EnvironmentModel(state_dim=2)
        prev = np.array([1.0, 0.0])
        next_s = np.array([1.1, 0.0])
        env.learn_transition(prev, np.zeros(2), next_s)
        assert len(env.learned_transitions) == 1

    def test_dynamics_uncertainty_positive(self):
        env = EnvironmentModel(state_dim=2)
        u = env.dynamics_uncertainty()
        assert u >= 0.0

    def test_predict_with_explicit_actions(self):
        env = EnvironmentModel(state_dim=2)
        env.set_state(np.array([1.0, 0.0]))
        actions = [np.array([0.5, 0.0])] * 3
        predictions = env.predict(horizon=3, actions=actions)
        assert predictions.shape == (4, 2)

    def test_set_state_updates_history(self):
        env = EnvironmentModel(state_dim=3)
        env.set_state(np.array([1.0, 2.0, 3.0]))
        assert len(env.history) == 1
        assert np.allclose(env.state, [1.0, 2.0, 3.0])
