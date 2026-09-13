import pytest
from app.router import choose_model

def test_choose_model():
    assert choose_model("simple") == "gpt-4o-mini"
    assert choose_model("medium") == "gpt-4o"
    assert choose_model("hard") == "gpt-4-turbo"
