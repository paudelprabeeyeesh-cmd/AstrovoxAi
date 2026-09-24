import pytest
from context_management.context_manager import ContextManager


class TestContextManager:
    def test_invalid_max_tokens(self):
        with pytest.raises(ValueError):
            ContextManager(max_tokens=0)

    def test_set_and_get_system_prompt(self):
        manager = ContextManager()
        manager.set_system_prompt("You are helpful.")
        context = manager.get_context()
        assert context[0]["role"] == "system"
        assert context[0]["content"] == "You are helpful."

    def test_add_turn(self):
        manager = ContextManager()
        turn = manager.add_turn("user", "Hello")
        assert turn == {"role": "user", "content": "Hello"}
        assert len(manager.get_context()) == 1

    def test_clear(self):
        manager = ContextManager()
        manager.add_turn("user", "Hi")
        manager.clear()
        assert manager.get_context() == []

    def test_token_count(self):
        manager = ContextManager()
        manager.add_turn("user", "one two three")
        manager.add_turn("assistant", "four five")
        assert manager.token_count() == 5

    def test_truncate_removes_oldest(self):
        manager = ContextManager(max_tokens=2)
        manager.add_turn("user", "one two three")
        manager.add_turn("assistant", "four five six")
        manager.truncate()
        assert manager.token_count() <= 2
