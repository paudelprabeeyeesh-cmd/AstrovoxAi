# Section 18 — Reinforcement Learning and Decision Mathematics

**Level 3–4** | Topics 737–775  
**Used in AstraVox:** agents that plan, choose tools, adapt to feedback, and make sequential decisions. Reinforcement learning is not required for every assistant feature.

737. Markov decision processes  
738. States, actions, and rewards  
739. Reward functions  
740. Discounted returns  
741. Bellman equations  
742. Value functions  
743. State-value functions  
744. Action-value functions  
745. Policy functions  
746. Dynamic programming for decision-making  
747. Policy evaluation  
748. Policy iteration  
749. Value iteration  
750. Monte Carlo methods  
751. Temporal-difference learning  
752. Q-learning  
753. SARSA  
754. Deep Q-networks  
755. Policy gradients  
756. Actor–critic methods  
757. Advantage estimation  
758. Generalized advantage estimation  
759. PPO objectives  
760. Exploration–exploitation trade-offs  
761. Entropy-regularized reinforcement learning  
762. Model-based reinforcement learning  
763. Planning under uncertainty  
764. Partially observable Markov decision processes  
765. Multi-agent reinforcement learning  
766. Inverse reinforcement learning  
767. Offline reinforcement learning  
768. Bandit algorithms  
769. Contextual bandits  
770. Regret bounds  
771. Reward-model uncertainty  
772. Safe reinforcement learning  
773. Decision theory  
774. Game theory  
775. Mechanism design  

## AI applications

Agents that plan, choose tools, adapt to feedback, and make sequential decisions. Reinforcement learning is not required for every assistant feature.

## Mapping to code

- `internal/rl/` — MDPs, Bellman equations, value/policy iteration, Q-learning, SARSA, DQN, policy gradients, actor-critic, PPO (topics 737–759).
- `internal/agents/` and `internal/planner/` — bandits, contextual bandits, regret bounds, planning under uncertainty, POMDPs (topics 760–764).
- `internal/grounding/` and reward modeling — reward functions, reward-model uncertainty, safe RL, inverse RL, offline RL (topics 739, 766–772).
- `internal/game/` — decision theory, game theory, mechanism design (topics 773–775).
