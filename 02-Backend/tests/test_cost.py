import pytest
from app.cost import count_tokens

def test_count_tokens():
    tokens = count_tokens("hello world", model="gpt-4o-mini")
    assert tokens > 0
