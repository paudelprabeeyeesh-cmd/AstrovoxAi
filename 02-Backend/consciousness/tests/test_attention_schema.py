import numpy as np

from consciousness.attention_schema import AttentionSchema


def test_schema_initialization():
    att = AttentionSchema()
    assert att.get_schema_state().sum() == 0.0


def test_update_attention_changes_intensity():
    att = AttentionSchema()
    s0 = att.update_attention(np.array([1.0, 0.0, 0.5, 0.3]))
    assert s0.intensity > 0.0


def test_form_schema_returns_array():
    att = AttentionSchema()
    schema = att.form_schema(np.array([0.1, 0.2, 0.3]))
    assert schema.size == att.capacity


def test_awareness_of_returns_float():
    att = AttentionSchema()
    att.form_schema(np.array([0.1, 0.2, 0.3]))
    score = att.awareness_of(np.array([0.1, 0.2, 0.3]))
    assert isinstance(score, float)


def test_reset_zeros_schema():
    att = AttentionSchema()
    att.form_schema(np.array([0.1, 0.2, 0.3]))
    att.reset()
    assert att.get_schema_state().sum() == 0.0
