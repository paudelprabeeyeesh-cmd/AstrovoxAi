from world_model.environment_model import EnvironmentModel


class TestEnvironmentModel:
    def test_step_changes_state(self):
        env = EnvironmentModel(state_dim=2)
        env.set_state([1.0, 0.0])
        new_state = env.step()
        assert len(new_state) == 2
        assert len(env.history) == 2

    def test_predict_horizon(self):
        env = EnvironmentModel(state_dim=2)
        env.set_state([1.0, 0.0])
        predictions = env.predict(horizon=3)
        assert len(predictions) == 4
        assert all(len(s) == 2 for s in predictions)

    def test_learn_transition_updates_noise(self):
        env = EnvironmentModel(state_dim=2)
        prev = [1.0, 0.0]
        next_s = [1.1, 0.0]
        env.learn_transition(prev, [0.0, 0.0], next_s)
        assert len(env.learned_transitions) == 1

    def test_dynamics_uncertainty_positive(self):
        env = EnvironmentModel(state_dim=2)
        u = env.dynamics_uncertainty()
        assert u >= 0.0

    def test_predict_with_explicit_actions(self):
        env = EnvironmentModel(state_dim=2)
        env.set_state([1.0, 0.0])
        actions = [[0.5, 0.0]] * 3
        predictions = env.predict(horizon=3, actions=actions)
        assert len(predictions) == 4
        assert all(len(s) == 2 for s in predictions)

    def test_set_state_updates_history(self):
        env = EnvironmentModel(state_dim=3)
        env.set_state([1.0, 2.0, 3.0])
        assert len(env.history) == 1
        assert env.state == [1.0, 2.0, 3.0]
