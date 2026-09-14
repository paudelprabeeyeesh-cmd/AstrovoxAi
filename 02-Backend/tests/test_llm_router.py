import pytest
from unittest.mock import MagicMock, patch
from app.core.router import call_llm


def make_response(text="hello", model="llama-3.1-8b-instant", tokens=10):
    mock = MagicMock()
    mock.choices[0].message.content = text
    mock.usage.total_tokens = tokens
    return mock


def test_call_llm_first_provider_success():
    with patch.dict("os.environ", {"GROQ_API_KEY": "sk-test"}):
        with patch("app.core.router.OpenAI") as MockOpenAI:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = make_response()
            MockOpenAI.return_value = mock_client
            result = call_llm("test prompt")
            assert result["text"] == "hello"
            assert result["provider"] == "groq"
            assert result["model"] == "llama-3.1-8b-instant"
            assert result["tokens"] == 10


def test_call_llm_fallback_to_second_provider():
    with patch.dict("os.environ", {"GROQ_API_KEY": "sk-test", "GEMINI_API_KEY": "sk-test"}):
        with patch("app.core.router.OpenAI") as MockOpenAI:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = [
                Exception("groq down"),
                make_response(text="gemini response", model="gemini-2.0-flash"),
            ]
            MockOpenAI.return_value = mock_client
            result = call_llm("test prompt")
            assert result["text"] == "gemini response"
            assert result["provider"] == "gemini"
            assert result["model"] == "gemini-2.0-flash"


def test_call_llm_all_providers_fail():
    with patch.dict("os.environ", {"GROQ_API_KEY": "sk-test"}):
        with patch("app.core.router.OpenAI") as MockOpenAI:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception("all down")
            MockOpenAI.return_value = mock_client
            with pytest.raises(RuntimeError, match="All LLM providers failed"):
                call_llm("test prompt")


def test_call_llm_no_providers_configured():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError, match="No AI provider configured"):
            call_llm("test prompt")
