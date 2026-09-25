import pytest
from unittest.mock import MagicMock
from app.core.moderation import check_moderation, is_safe, MODERATION_CATEGORIES


def test_is_safe_clean():
    assert is_safe("What is the weather today?") is True


def test_check_moderation_flagged():
    mock_categories = MagicMock()
    for category in MODERATION_CATEGORIES:
        attr = category.replace("/", "_")
        setattr(mock_categories, attr, False)
    setattr(mock_categories, "hate_threatening", True)
    
    mock_result = MagicMock()
    mock_result.categories = mock_categories
    
    mock_client = MagicMock()
    mock_client.moderations.create.return_value = MagicMock(results=[mock_result])
    
    import openai
    original_openai = openai.OpenAI
    openai.OpenAI = lambda: mock_client
    try:
        flagged, category = check_moderation("I want to hurt someone")
        assert flagged is True
    finally:
        openai.OpenAI = original_openai


def test_check_moderation_clean():
    mock_categories = MagicMock()
    for category in MODERATION_CATEGORIES:
        attr = category.replace("/", "_")
        setattr(mock_categories, attr, False)
    
    mock_result = MagicMock()
    mock_result.categories = mock_categories
    
    mock_client = MagicMock()
    mock_client.moderations.create.return_value = MagicMock(results=[mock_result])
    
    import openai
    original_openai = openai.OpenAI
    openai.OpenAI = lambda: mock_client
    try:
        flagged, category = check_moderation("What is the weather today?")
        assert flagged is False
    finally:
        openai.OpenAI = original_openai
