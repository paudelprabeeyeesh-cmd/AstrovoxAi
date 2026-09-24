import numpy as np
from ..curiosity_driven import CuriosityDriven


class TestCuriosityDriven:
    def test_initialization(self):
        cd = CuriosityDriven(state_dim=8)
        assert cd.state_dim == 8
        assert cd.epsilon == 0.1

    def test_compute_curiosity_new_state(self):
        cd = CuriosityDriven(epsilon=0.5)
        state = np.random.randn(8)
        curiosity, key = cd.compute_curiosity(state, 0.0)
        assert 0.0 <= curiosity <= 1.0
        assert key in cd.state_bank

    def test_compute_curiosity_visited(self):
        cd = CuriosityDriven(epsilon=0.5)
        state = np.ones(8)
        c1, _ = cd.compute_curiosity(state, 0.0)
        c2, _ = cd.compute_curiosity(state, 0.0)
        assert c2 <= c1

    def test_select_action_explore(self):
        cd = CuriosityDriven(epsilon=1.0)
        state = np.ones(8)
        cd.compute_curiosity(state, 0.0)
        q = np.array([0.0, 1.0, 0.0])
        action = cd.select_action(state, q)
        assert 0 <= action < len(q)

    def test_select_action_exploit(self):
        cd = CuriosityDriven(epsilon=0.0)
        state = np.ones(8)
        cd.compute_curiosity(state, 0.0)
        q = np.array([0.0, 1.0, 0.0])
        action = cd.select_action(state, q)
        assert action == 1

    def test_update_epsilon_decay(self):
        cd = CuriosityDriven(epsilon=0.5, decay=0.5)
        old_eps = cd.epsilon
        cd.update_epsilon()
        assert cd.epsilon == max(0.01, old_eps * 0.5)

    def test_get_state_novelty(self):
        cd = CuriosityDriven()
        state = np.ones(8)
        assert cd.get_state_novelty(state) == 1.0
        cd.compute_curiosity(state, 0.0)
        assert cd.get_state_novelty(state) < 1.0

    def test_exploration_stats(self):
        cd = CuriosityDriven()
        state = np.ones(8)
        cd.compute_curiosity(state, 0.0)
        stats = cd.get_exploration_stats()
        assert "mean_curiosity" in stats
        assert stats["visited_states"] == 1

    def test_decay_states(self):
        cd = CuriosityDriven()
        state = np.ones(8)
        cd.compute_curiosity(state, 0.0)
        for _ in range(250):
            cd.decay_states(half_life=100.0)
        stats = cd.get_exploration_stats()
        assert stats["visited_states"] == 0
