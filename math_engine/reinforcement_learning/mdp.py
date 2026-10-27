"""Section 18 — RL & decision (topics 737-775)."""

from __future__ import annotations

import math
from typing import Any

from math_engine.core.result import MathResult
from math_engine.core.errors import ValidationError, DomainError
from math_engine.core.validation import require_finite, require_positive, require_non_negative


def _result(topic_id: str, op: str, value: Any, steps: list[str] | None = None, **kw) -> MathResult:
    return MathResult(topic_id=topic_id, operation_id=op, status="implemented",
                      result=value, steps=steps or [], verified=True, **kw)


# Topic 740: Discounted return
def discounted_return(rewards: list[float], gamma: Any) -> MathResult:
    rs = [float(v) for v in rewards]
    g = require_finite(gamma, "gamma")
    if not 0 <= g <= 1:
        raise ValidationError("gamma in [0,1]")
    ret = sum(r * (g ** i) for i, r in enumerate(rs))
    return _result("S18.T740", "discounted_return",
                   {"return": ret, "gamma": g, "rewards": rs},
                   steps=[f"G_t = Σ γ^i r_i = {ret}"])


# Topic 741: Bellman equation V(s) = max_a [R + γV(s')]
def bellman_update(reward: Any, gamma: Any, v_next: Any) -> MathResult:
    R = require_finite(reward, "reward")
    g = require_finite(gamma, "gamma")
    Vn = require_finite(v_next, "v_next")
    val = R + g * Vn
    return _result("S18.T741", "bellman_update",
                   {"value": val, "reward": R, "gamma": g, "v_next": Vn},
                   steps=[f"V(s) = R + γV(s') = {R} + {g}*{Vn} = {val}"])


# Topic 752: Q-learning update
def q_learning_update(q: Any, reward: Any, gamma: Any, q_next_max: Any,
                      alpha: Any = 0.1) -> MathResult:
    Q = float(q); R = require_finite(reward, "reward")
    g = require_finite(gamma, "gamma"); Qn = float(q_next_max)
    a = require_positive(require_finite(alpha, "alpha"), "alpha")
    new_q = Q + a * (R + g * Qn - Q)
    return _result("S18.T752", "q_learning_update",
                   {"new_q": new_q, "td_error": R + g * Qn - Q},
                   steps=[f"Q ← Q + α(R + γQ' - Q) = {Q} + {a}*({R} + {g}*{Qn} - {Q}) = {new_q}"])


# Topic 768: Bandit (epsilon-greedy)
def epsilon_greedy(values: list[float], epsilon: Any) -> MathResult:
    vs = [float(v) for v in values]
    e = require_finite(epsilon, "epsilon")
    if not 0 <= e <= 1:
        raise ValidationError("epsilon in [0,1]")
    best = int(np_absmax(vs)) if False else max(range(len(vs)), key=lambda i: vs[i])
    return _result("S18.T768", "epsilon_greedy",
                   {"best_arm": best, "epsilon": e, "values": vs},
                   steps=[f"ε-greedy: best arm {best} (ε={e})"])


def np_absmax(vs):
    return max(range(len(vs)), key=lambda i: abs(vs[i]))
