import numpy as np

from consciousness.enactive_ai import EnactiveAgent


def test_act_returns_vector():
    agent = EnactiveAgent()
    v = agent.act(np.array([0.1, 0.2]))
    assert v.size == 32


def test_make_sense_updates_state():
    agent = EnactiveAgent()
    st = agent.make_sense(np.array([0.1] * 32), label="s1")
    assert st.label == "s1"


def test_sense_making_history_non_empty():
    agent = EnactiveAgent()
    agent.make_sense(np.array([0.1] * 32), label="s1")
    assert len(agent.sense_making_history()) == 1
