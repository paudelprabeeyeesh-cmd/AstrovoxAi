import pytest
from app.fallback import safe_answer

def test_safe_answer():
    assert safe_answer(0.9) == "answer"
    assert safe_answer(0.6) == "I don't know — ask human"
    assert safe_answer(0.3) == "human review required"
