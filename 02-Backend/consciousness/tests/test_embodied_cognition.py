import numpy as np
import pytest

from consciousness.embodied_cognition import EmbodiedAgent


def test_body_schema_returns_vector():
    agent = EmbodiedAgent()
    vector = agent.body_schema()
    assert vector.size == 24


def test_sense_motor_loop_returns_state():
    agent = EmbodiedAgent()
    state = agent.sense_motor_loop(
        touch=np.array([0.1, 0.2]),
        proprioception=np.array([0.3, 0.4]),
        action=np.array([0.5, 0.6]),
    )
    assert state is not None
