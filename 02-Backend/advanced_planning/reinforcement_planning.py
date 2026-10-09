import math
import random
from typing import Dict, List, Optional, Sequence


class QTable:
    def __init__(self, state_size: int, action_size: int, lr: float = 0.1, gamma: float = 0.99, epsilon: float = 1.0,
                 epsilon_decay: float = 0.995, epsilon_min: float = 0.01):
        self.q_table: List[List[float]] = [[0.0] * action_size for _ in range(state_size)]
        self.lr = lr
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.training_error: List[float] = []

    def get_action(self, state: int, explore: bool = True) -> int:
        if explore and random.random() < self.epsilon:
            return random.randint(0, len(self.q_table[0]) - 1)
        return max(range(len(self.q_table[state])), key=lambda a: self.q_table[state][a])

    def update(self, state: int, action: int, reward: float, next_state: int, done: bool) -> None:
        current = self.q_table[state][action]
        next_max = max(self.q_table[next_state])
        target = reward + (1 - done) * self.gamma * next_max
        td_error = target - current
        self.q_table[state][action] = current + self.lr * td_error
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

    def get_best_policy(self) -> List[int]:
        return [max(range(len(self.q_table.q_table[s])), key=lambda a: self.q_table.q_table[s][a])
                for s in range(self.num_states)]

    def get_policy_value(self, state: int) -> float:
        return float(max(self.q_table.q_table[state]))


class PolicyGradientPlanner:
    def __init__(self, num_states: int, num_actions: int, lr: float = 0.01):
        self.num_states = num_states
        self.num_actions = num_actions
        self.theta: List[List[float]] = [[random.gauss(0, 0.01) for _ in range(num_actions)]
                                          for _ in range(num_states)]
        self.lr = lr
        self.losses: List[float] = []

    def softmax(self, state: int) -> List[float]:
        logits = self.theta[state]
        m = max(logits)
        e = [math.exp(x - m) for x in logits]
        s = sum(e)
        return [x / s for x in e]

    def get_action(self, state: int) -> int:
        probs = self.softmax(state)
        r = random.random()
        cumsum = 0.0
        for a, p in enumerate(probs):
            cumsum += p
            if r <= cumsum:
                return a
        return self.num_actions - 1

    def update(self, states: List[int], actions: List[int], rewards: List[float]) -> None:
        returns = self._discount_rewards(rewards)
        for s, a, g in zip(states, actions, returns):
            probs = self.softmax(s)
            grad = [-p for p in probs]
            grad[a] += 1.0
            self.theta[s] = [th + self.lr * g * gr for th, gr in zip(self.theta[s], grad)]
            self.losses.append(-g * math.log(max(probs[a], 1e-10)))

    def _discount_rewards(self, rewards: List[float], gamma: float = 0.99) -> List[float]:
        returns = [0.0] * len(rewards)
        running = 0.0
        for i in range(len(rewards) - 1, -1, -1):
            running = rewards[i] + gamma * running
            returns[i] = running
        if len(returns) > 1:
            mean_r = sum(returns) / len(returns)
            var_r = sum((x - mean_r) ** 2 for x in returns) / len(returns)
            std_r = math.sqrt(var_r) + 1e-8
            returns = [(x - mean_r) / std_r for x in returns]
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
