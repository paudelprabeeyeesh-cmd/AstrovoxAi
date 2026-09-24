
import numpy as np
from typing import List


class QTable:
    def __init__(self, state_size: int, action_size: int, lr: float = 0.1, gamma: float = 0.99, epsilon: float = 1.0,
                 epsilon_decay: float = 0.995, epsilon_min: float = 0.01):
        self.q_table = np.zeros((state_size, action_size))
        self.lr = lr
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.training_error: List[float] = []

    def get_action(self, state: int, explore: bool = True) -> int:
        if explore and np.random.random() < self.epsilon:
            return np.random.randint(0, self.q_table.shape[1])
        return int(np.argmax(self.q_table[state]))

    def update(self, state: int, action: int, reward: float, next_state: int, done: bool) -> None:
        current = self.q_table[state, action]
        target = reward + (1 - done) * self.gamma * np.max(self.q_table[next_state])
        td_error = target - current
        self.q_table[state, action] = current + self.lr * td_error
        self.training_error.append(abs(td_error))

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)


class RLPlanner:
    def __init__(self, num_states: int, num_actions: int):
        self.q_table = QTable(num_states, num_actions)
        self.num_states = num_states
        self.num_actions = num_actions
        self.episode_rewards: List[float] = []

    def train_episode(self, env, max_steps: int = 100) -> float:
        state = env.reset()
        total_reward = 0.0
        done = False
        for _ in range(max_steps):
            action = self.q_table.get_action(state, explore=True)
            next_state, reward, done, _ = env.step(action)
            self.q_table.update(state, action, reward, next_state, done)
            total_reward += reward
            state = next_state
            if done:
                break
        self.q_table.decay_epsilon()
        self.episode_rewards.append(total_reward)
        return total_reward

    def train(self, env, num_episodes: int = 500, max_steps: int = 100) -> List[float]:
        rewards = []
        for _ in range(num_episodes):
            r = self.train_episode(env, max_steps)
            rewards.append(r)
        return rewards

    def get_best_policy(self) -> np.ndarray:
        return np.argmax(self.q_table.q_table, axis=1)

    def get_policy_value(self, state: int) -> float:
        return float(np.max(self.q_table.q_table[state]))


class PolicyGradientPlanner:
    def __init__(self, num_states: int, num_actions: int, lr: float = 0.01):
        self.num_states = num_states
        self.num_actions = num_actions
        self.theta = np.random.randn(num_states, num_actions) * 0.01
        self.lr = lr
        self.losses: List[float] = []

    def softmax(self, state: int) -> np.ndarray:
        logits = self.theta[state]
        e = np.exp(logits - np.max(logits))
        return e / np.sum(e)

    def get_action(self, state: int) -> int:
        probs = self.softmax(state)
        return int(np.random.choice(self.num_actions, p=probs))

    def update(self, states: List[int], actions: List[int], rewards: List[float]) -> None:
        returns = self._discount_rewards(rewards)
        for s, a, g in zip(states, actions, returns):
            probs = self.softmax(s)
            grad = -probs
            grad[a] += 1.0
            self.theta[s] += self.lr * g * grad
            self.losses.append(-g * np.log(max(probs[a], 1e-10)))

    def _discount_rewards(self, rewards: List[float], gamma: float = 0.99) -> np.ndarray:
        returns = np.zeros(len(rewards))
        running = 0.0
        for i in range(len(rewards) - 1, -1, -1):
            running = rewards[i] + gamma * running
            returns[i] = running
        if len(returns) > 1:
            returns = (returns - returns.mean()) / (returns.std() + 1e-8)
        return returns

    def train_episode(self, env, max_steps: int = 100) -> float:
        state = env.reset()
        states, actions, rewards = [], [], []
        total_reward = 0.0
        done = False
        for _ in range(max_steps):
            action = self.get_action(state)
            next_state, reward, done, _ = env.step(action)
            states.append(state)
            actions.append(action)
            rewards.append(reward)
            total_reward += reward
            state = next_state
            if done:
                break
        self.update(states, actions, rewards)
        return total_reward
