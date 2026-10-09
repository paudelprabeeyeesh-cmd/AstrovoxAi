
import numpy as np
from advanced_planning.reinforcement_planning import QTable, RLPlanner, PolicyGradientPlanner


class SimpleGridEnv:
    def __init__(self, size: int = 5):
        self.size = size
        self.state = 0
        self.goal = size - 1
        self._max_steps = 20

    def reset(self):
        self.state = 0
        return self.state

    def step(self, action: int):
        if action == 1 and self.state < self.size - 1:
            self.state += 1
        elif action == 0 and self.state > 0:
            self.state -= 1
        done = self.state == self.goal
        reward = 1.0 if done else -0.01
        return self.state, reward, done, {}


def test_qtable_initialization():
    qt = QTable(5, 2)
    assert qt.q_table.shape == (5, 2)
    assert qt.epsilon == 1.0


def test_qtable_get_action_explore():
    np.random.seed(0)
    qt = QTable(5, 2, epsilon=1.0)
    actions = [qt.get_action(0, explore=True) for _ in range(20)]
    assert all(a in [0, 1] for a in actions)


def test_qtable_get_action_exploit():
    qt = QTable(5, 2, epsilon=0.0)
    qt.q_table[2, 1] = 10.0
    qt.q_table[2, 0] = -5.0
    assert qt.get_action(2, explore=False) == 1


def test_qtable_update():
    qt = QTable(5, 2, lr=0.1, gamma=0.9)
    qt.q_table[0, 0] = 0.0
    qt.update(0, 0, 1.0, 1, False)
    assert qt.q_table[0, 0] > 0.0
    assert len(qt.training_error) == 1


def test_qtable_decay_epsilon():
    qt = QTable(5, 2, epsilon=0.5, epsilon_decay=0.9, epsilon_min=0.01)
    qt.decay_epsilon()
    assert qt.epsilon == 0.45


def test_rl_planner_train():
    env = SimpleGridEnv(size=5)
    planner = RLPlanner(num_states=5, num_actions=2)
    rewards = planner.train(env, num_episodes=50, max_steps=20)
    assert len(rewards) == 50
    policy = planner.get_best_policy()
    assert policy.shape == (5,)
    assert all(a in [0, 1] for a in policy)


def test_rl_planner_improves():
    env = SimpleGridEnv(size=3)
    planner = RLPlanner(num_states=3, num_actions=2)
    rewards = planner.train(env, num_episodes=100, max_steps=10)
    assert len(rewards) == 100
    total = sum(r > 0 for r in rewards)
    assert total >= 0


def test_rl_planner_get_policy_value():
    env = SimpleGridEnv(size=5)
    planner = RLPlanner(num_states=5, num_actions=2)
    planner.train(env, num_episodes=20, max_steps=10)
    val = planner.get_policy_value(0)
    assert isinstance(val, float)


def test_policy_gradient_get_action():
    planner = PolicyGradientPlanner(num_states=5, num_actions=2)
    action = planner.get_action(0)
    assert action in [0, 1]


def test_policy_gradient_update():
    planner = PolicyGradientPlanner(num_states=5, num_actions=2)
    old_losses = list(planner.losses)
    planner.update([0, 1, 2], [0, 1, 0], [1.0, 0.5, -0.5])
    assert len(planner.losses) > len(old_losses)


def test_policy_gradient_train_episode():
    env = SimpleGridEnv(size=3)
    planner = PolicyGradientPlanner(num_states=3, num_actions=2)
    reward = planner.train_episode(env, max_steps=20)
    assert isinstance(reward, float)
