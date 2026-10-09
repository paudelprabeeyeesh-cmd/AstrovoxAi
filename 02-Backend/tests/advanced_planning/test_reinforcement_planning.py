
import numpy as np
from advanced_planning.reinforcement_planning import QTable, RLPlanner, PolicyGradientPlanner


class DummyEnv:
    def __init__(self, n_states=4, n_actions=2):
        self.n_states = n_states
        self.n_actions = n_actions
        self._state = 0

    def reset(self):
        self._state = 0
        return self._state

    def step(self, action):
        self._state = (self._state + action) % self.n_states
        reward = 1.0 if self._state == 0 else -0.1
        done = self._state == 0
        return self._state, reward, done, {}


class TestQTable:

    def test_initial_values_zero(self):
        qt = QTable(4, 2)
        assert qt.q_table.shape == (4, 2)
        assert np.all(qt.q_table == 0.0)

    def test_get_action_exploit(self):
        qt = QTable(2, 3, epsilon=0.0)
        qt.q_table[0] = [0.1, 0.9, 0.5]
        action = qt.get_action(0, explore=True)
        assert action == 1

    def test_get_action_explore(self):
        qt = QTable(2, 3, epsilon=1.0)
        np.random.seed(0)
        action = qt.get_action(0, explore=True)
        assert 0 <= action < 3

    def test_update_changes_q_value(self):
        qt = QTable(4, 2, lr=0.5, gamma=0.0)
        qt.update(0, 0, 1.0, 1, False)
        assert qt.q_table[0, 0] == 0.5

    def test_update_done_sets_target_to_reward(self):
        qt = QTable(4, 2, lr=1.0, gamma=0.0)
        qt.update(0, 0, 5.0, 1, True)
        assert qt.q_table[0, 0] == 5.0

    def test_decay_epsilon_decreases(self):
        qt = QTable(4, 2, epsilon=0.5, epsilon_decay=0.5, epsilon_min=0.01)
        qt.decay_epsilon()
        assert abs(qt.epsilon - 0.25) < 1e-9

    def test_decay_epsilon_respects_min(self):
        qt = QTable(4, 2, epsilon=0.01, epsilon_decay=0.5, epsilon_min=0.01)
        qt.decay_epsilon()
        assert qt.epsilon == 0.01

    def test_training_error_recorded(self):
        qt = QTable(4, 2, lr=1.0, gamma=0.0)
        qt.update(0, 0, 1.0, 1, False)
        assert len(qt.training_error) == 1
        assert qt.training_error[0] == 1.0


class TestRLPlanner:

    def test_train_returns_rewards_list(self):
        planner = RLPlanner(4, 2)
        env = DummyEnv()
        np.random.seed(0)
        rewards = planner.train(env, num_episodes=5, max_steps=10)
        assert isinstance(rewards, list)
        assert len(rewards) == 5

    def test_episode_rewards_recorded(self):
        planner = RLPlanner(4, 2)
        env = DummyEnv()
        np.random.seed(0)
        planner.train(env, num_episodes=3, max_steps=10)
        assert len(planner.episode_rewards) == 3

    def test_get_best_policy_shape(self):
        planner = RLPlanner(3, 2)
        policy = planner.get_best_policy()
        assert policy.shape == (3,)
        assert all(0 <= a < 2 for a in policy)

    def test_get_policy_value(self):
        planner = RLPlanner(3, 2)
        planner.q_table.q_table[1] = [0.1, 0.9]
        val = planner.get_policy_value(1)
        assert abs(val - 0.9) < 1e-9


class TestPolicyGradientPlanner:

    def test_softmax_sums_to_one(self):
        pg = PolicyGradientPlanner(3, 2)
        probs = pg.softmax(0)
        assert abs(probs.sum() - 1.0) < 1e-6
        assert np.all(probs >= 0.0)

    def test_get_action_returns_valid_index(self):
        pg = PolicyGradientPlanner(3, 2)
        np.random.seed(0)
        action = pg.get_action(0)
        assert 0 <= action < 2

    def test_train_episode_updates_losses(self):
        pg = PolicyGradientPlanner(4, 2)
        env = DummyEnv()
        np.random.seed(0)
        total = pg.train_episode(env, max_steps=20)
        assert isinstance(total, float)
        assert len(pg.losses) > 0

    def test_discounted_rewards_monotonically_decay(self):
        pg = PolicyGradientPlanner(1, 1)
        rewards = [1.0, 1.0, 1.0]
        returns = pg._discount_rewards(rewards)
        assert len(returns) == 3
        assert returns[0] >= returns[1] >= returns[2]

    def test_discount_normalization(self):
        pg = PolicyGradientPlanner(1, 1)
        rewards = [0.0, 1.0, 0.0]
        returns = pg._discount_rewards(rewards)
        assert abs(returns.mean()) < 1e-6
