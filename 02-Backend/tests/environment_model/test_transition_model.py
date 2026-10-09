import random
from world_model.environment_model import DynamicsModel, TransitionModel


class TestTransitionModel:
    def test_step_returns_correct_length(self):
        model = TransitionModel(state_dim=3)
        state = [1.0, 0.0, 0.0]
        next_state = model.step(state, [0.1, 0.0, 0.0])
        assert len(next_state) == 3

    def test_step_mutates_state(self):
        model = TransitionModel(state_dim=2)
        state = [0.0, 0.0]
        next_state = model.step(state, [0.0, 0.0])
        assert next_state is not state

    def test_update_stores_transition(self):
        model = TransitionModel(state_dim=2)
        model.update([1.0, 0.0], [0.0, 0.0], [1.1, 0.0])
        assert len(model.learned_transitions) == 1
        assert model.learned_transitions[0][0] == [1.0, 0.0]

    def test_noise_covariance_updates_after_multiple_transitions(self):
        random.seed(42)
        model = TransitionModel(state_dim=2)
        model.update([1.0, 0.0], [0.0, 0.0], [1.1, 0.0])
        model.update([1.1, 0.0], [0.0, 0.0], [1.2, 0.0])
        trace = sum(model.noise_covariance[i][i] for i in range(2))
        assert trace > 0.0
