"""Tests for the AI provider abstraction layer."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.providers.base import ChatMessage, ChatResponse, ProviderConfig, EmbeddingVector
from app.providers.models import (
    get_model_info,
    get_provider_for_model,
    is_valid_model,
    list_models,
)

# Conditional imports for providers with optional dependencies
try:
    from app.providers.openai_provider import OpenAIProvider
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from app.providers.anthropic_provider import AnthropicProvider
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from app.providers.gemini_provider import GeminiProvider
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from app.providers.ollama_provider import OllamaProvider
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


# ============================================================================
# Model Registry Tests
# ============================================================================

class TestModelRegistry:
    def test_is_valid_model_openai(self):
        assert is_valid_model("gpt-4") is True
        assert is_valid_model("gpt-4o-mini") is True
        assert is_valid_model("gpt-3.5-turbo") is True

    def test_is_valid_model_anthropic(self):
        assert is_valid_model("claude-3-5-sonnet") is True
        assert is_valid_model("claude-3-opus") is True
        assert is_valid_model("claude-3-haiku") is True

    def test_is_valid_model_gemini(self):
        assert is_valid_model("gemini-1.5-pro") is True
        assert is_valid_model("gemini-1.5-flash") is True
        assert is_valid_model("gemini-1.0-pro") is True

    def test_is_valid_model_ollama(self):
        assert is_valid_model("llama3") is True
        assert is_valid_model("mistral") is True
        assert is_valid_model("codellama") is True

    def test_is_valid_model_invalid(self):
        assert is_valid_model("gpt-5") is False
        assert is_valid_model("claude-4") is False
        assert is_valid_model("") is False
        assert is_valid_model("nonexistent") is False

    def test_get_provider_for_model(self):
        assert get_provider_for_model("gpt-4") == "openai"
        assert get_provider_for_model("claude-3-5-sonnet") == "anthropic"
        assert get_provider_for_model("gemini-1.5-pro") == "gemini"
        assert get_provider_for_model("llama3") == "ollama"
        assert get_provider_for_model("nonexistent") is None

    def test_get_model_info(self):
        info = get_model_info("gpt-4")
        assert info is not None
        assert info.provider == "openai"
        assert info.display_name == "GPT-4"

        info = get_model_info("claude-3-5-sonnet")
        assert info is not None
        assert info.id == "claude-3-5-sonnet-20241022"

    def test_list_models_all(self):
        models = list_models()
        assert len(models) >= 10

    def test_list_models_by_provider(self):
        openai_models = list_models("openai")
        assert len(openai_models) == 3
        assert all(m.provider == "openai" for m in openai_models)

        anthropic_models = list_models("anthropic")
        assert len(anthropic_models) == 3

        gemini_models = list_models("gemini")
        assert len(gemini_models) == 3

        ollama_models = list_models("ollama")
        assert len(ollama_models) >= 5


# ============================================================================
# Provider Base Tests
# ============================================================================

class TestProviderBase:
    def test_chat_message_creation(self):
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_chat_response_creation(self):
        resp = ChatResponse(content="Hi", model="gpt-4", provider="openai")
        assert resp.content == "Hi"
        assert resp.tokens_used is None
        assert resp.metadata == {}

    def test_provider_config_defaults(self):
        config = ProviderConfig(api_key="test")
        assert config.api_key == "test"
        assert config.base_url is None
        assert config.timeout == 60
        assert config.max_retries == 2

    def test_embedding_vector_creation(self):
        vec = EmbeddingVector(vector=[0.1, 0.2, 0.3], model="embedding-001")
        assert vec.vector == [0.1, 0.2, 0.3]
        assert vec.model == "embedding-001"
        assert vec.tokens_used is None

    def test_sanitize_error_redacts_openai_key(self):
        from app.providers.base import AIProvider
        provider = AIProvider(ProviderConfig(api_key="test"))
        error = Exception("Invalid API key: sk-abc123def456ghi789jkl012mno345pqr")
        sanitized = provider.sanitize_error(error)
        assert "REDACTED" in sanitized or "redacted" in sanitized.lower()

    def test_sanitize_error_redacts_anthropic_key(self):
        from app.providers.base import AIProvider
        provider = AIProvider(ProviderConfig(api_key="test"))
        error = Exception("Invalid key: sk-ant-abc123def456ghi789jkl012mno345pqr")
        sanitized = provider.sanitize_error(error)
        assert "REDACTED" in sanitized or "redacted" in sanitized.lower()

    def test_sanitize_error_redacts_google_key(self):
        from app.providers.base import AIProvider
        provider = AIProvider(ProviderConfig(api_key="test"))
        error = Exception("Invalid key: AIzaSyAbc123def456ghi789jkl012mno345pqr")
        sanitized = provider.sanitize_error(error)
        assert "REDACTED" in sanitized or "redacted" in sanitized.lower()

    def test_sanitize_error_redacts_bearer_token(self):
        from app.providers.base import AIProvider
        provider = AIProvider(ProviderConfig(api_key="test"))
        error = Exception("Authorization: Bearer secret-token-12345")
        sanitized = provider.sanitize_error(error)
        assert "REDACTED" in sanitized or "redacted" in sanitized.lower()

    @pytest.mark.asyncio
    async def test_embed_not_implemented_by_default(self):
        from app.providers.base import AIProvider
        provider = AIProvider(ProviderConfig(api_key="test"))
        with pytest.raises(NotImplementedError):
            await provider.embed(["test"])


# ============================================================================
# Retry Logic Tests
# ============================================================================

class TestRetryLogic:
    @pytest.mark.asyncio
    async def test_chat_with_retry_succeeds_first_try(self):
        from app.providers.base import AIProvider
        provider = AIProvider(ProviderConfig(api_key="test", max_retries=2))
        provider.chat = AsyncMock(return_value=ChatResponse(content="Hi", model="test"))
        result = await provider.chat_with_retry(
            messages=[ChatMessage(role="user", content="Hello")],
            model="test",
        )
        assert result.content == "Hi"
        assert provider.chat.call_count == 1

    @pytest.mark.asyncio
    async def test_chat_with_retry_on_transient_error(self):
        from app.providers.base import AIProvider
        provider = AIProvider(ProviderConfig(api_key="test", max_retries=2))
        mock = AsyncMock(
            side_effect=[
                Exception("timeout error"),
                ChatResponse(content="Hi", model="test"),
            ]
        )
        provider.chat = mock
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await provider.chat_with_retry(
                messages=[ChatMessage(role="user", content="Hello")],
                model="test",
            )
        assert result.content == "Hi"
        assert mock.call_count == 2

    @pytest.mark.asyncio
    async def test_chat_with_retry_exhausts_retries(self):
        from app.providers.base import AIProvider
        provider = AIProvider(ProviderConfig(api_key="test", max_retries=1))
        provider.chat = AsyncMock(side_effect=Exception("timeout error"))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(Exception, match="timeout"):
                await provider.chat_with_retry(
                    messages=[ChatMessage(role="user", content="Hello")],
                    model="test",
                )
        assert provider.chat.call_count == 2

    @pytest.mark.asyncio
    async def test_chat_with_retry_no_retry_on_permanent_error(self):
        from app.providers.base import AIProvider
        provider = AIProvider(ProviderConfig(api_key="test", max_retries=2))
        provider.chat = AsyncMock(side_effect=Exception("invalid model name"))
        with pytest.raises(Exception, match="invalid model"):
            await provider.chat_with_retry(
                messages=[ChatMessage(role="user", content="Hello")],
                model="test",
            )
        assert provider.chat.call_count == 1


# ============================================================================
# OpenAI Provider Tests
# ============================================================================

@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
class TestOpenAIProvider:
    def test_init_without_key(self):
        provider = OpenAIProvider(ProviderConfig(api_key=None))
        assert provider.is_configured is False

    def test_init_with_key(self):
        provider = OpenAIProvider(ProviderConfig(api_key="sk-test"))
        assert provider.is_configured is True
        assert provider.name == "openai"

    def test_validate_model(self):
        provider = OpenAIProvider(ProviderConfig(api_key="test"))
        assert provider.validate_model("gpt-4") is True
        assert provider.validate_model("gpt-3.5-turbo") is True
        assert provider.validate_model("claude-3-5-sonnet") is False
        assert provider.validate_model("llama3") is False

    @pytest.mark.asyncio
    async def test_chat_without_key_raises(self):
        provider = OpenAIProvider(ProviderConfig(api_key=None))
        with pytest.raises(RuntimeError, match="not configured"):
            await provider.chat(
                messages=[ChatMessage(role="user", content="Hi")],
                model="gpt-4",
            )

    def test_sanitize_error_redacts_keys(self):
        provider = OpenAIProvider(ProviderConfig(api_key="test"))
        error = Exception("Invalid API key: sk-abc123def456ghi789jkl012mno345pqr")
        sanitized = provider.sanitize_error(error)
        assert "REDACTED" in sanitized or "redacted" in sanitized.lower()

    def test_supports_streaming(self):
        provider = OpenAIProvider(ProviderConfig(api_key="test"))
        assert provider.supports_streaming is True


# ============================================================================
# Anthropic Provider Tests
# ============================================================================

@pytest.mark.skipif(not ANTHROPIC_AVAILABLE, reason="anthropic package not installed")
class TestAnthropicProvider:
    def test_init_without_key(self):
        provider = AnthropicProvider(ProviderConfig(api_key=None))
        assert provider.is_configured is False

    def test_init_with_key(self):
        provider = AnthropicProvider(ProviderConfig(api_key="sk-ant-test"))
        assert provider.is_configured is True
        assert provider.name == "anthropic"

    def test_validate_model(self):
        provider = AnthropicProvider(ProviderConfig(api_key="test"))
        assert provider.validate_model("claude-3-5-sonnet") is True
        assert provider.validate_model("claude-3-opus") is True
        assert provider.validate_model("gpt-4") is False
        assert provider.validate_model("llama3") is False

    @pytest.mark.asyncio
    async def test_chat_without_key_raises(self):
        provider = AnthropicProvider(ProviderConfig(api_key=None))
        with pytest.raises(RuntimeError, match="not configured"):
            await provider.chat(
                messages=[ChatMessage(role="user", content="Hi")],
                model="claude-3-5-sonnet-20241022",
            )

    def test_supports_streaming(self):
        provider = AnthropicProvider(ProviderConfig(api_key="test"))
        assert provider.supports_streaming is True


# ============================================================================
# Gemini Provider Tests
# ============================================================================

@pytest.mark.skipif(not GEMINI_AVAILABLE, reason="google-generativeai not installed")
class TestGeminiProvider:
    def test_init_without_key(self):
        provider = GeminiProvider(ProviderConfig(api_key=None))
        assert provider.is_configured is False

    def test_init_with_key(self):
        provider = GeminiProvider(ProviderConfig(api_key="test-key"))
        assert provider.is_configured is True
        assert provider.name == "gemini"

    def test_validate_model(self):
        provider = GeminiProvider(ProviderConfig(api_key="test"))
        assert provider.validate_model("gemini-1.5-pro") is True
        assert provider.validate_model("gemini-1.5-flash") is True
        assert provider.validate_model("gpt-4") is False
        assert provider.validate_model("claude-3-5-sonnet") is False

    @pytest.mark.asyncio
    async def test_chat_without_key_raises(self):
        provider = GeminiProvider(ProviderConfig(api_key=None))
        with pytest.raises(RuntimeError, match="not configured"):
            await provider.chat(
                messages=[ChatMessage(role="user", content="Hi")],
                model="gemini-1.5-pro",
            )

    def test_supports_streaming(self):
        provider = GeminiProvider(ProviderConfig(api_key="test"))
        assert provider.supports_streaming is True

    @pytest.mark.asyncio
    async def test_embed_without_key_raises(self):
        provider = GeminiProvider(ProviderConfig(api_key=None))
        with pytest.raises(RuntimeError, match="not configured"):
            await provider.embed(["test text"])


# ============================================================================
# Ollama Provider Tests
# ============================================================================

@pytest.mark.skipif(not OLLAMA_AVAILABLE, reason="httpx not installed")
class TestOllamaProvider:
    def test_init(self):
        provider = OllamaProvider(ProviderConfig(base_url="http://localhost:11434"))
        assert provider.is_configured is True
        assert provider.name == "ollama"
        assert provider.config.base_url == "http://localhost:11434"

    def test_validate_model(self):
        provider = OllamaProvider()
        assert provider.validate_model("llama3") is True
        assert provider.validate_model("mistral") is True
        assert provider.validate_model("gpt-4") is False
        assert provider.validate_model("claude-3-5-sonnet") is False

    @pytest.mark.asyncio
    async def test_chat_server_unreachable(self):
        provider = OllamaProvider(ProviderConfig(base_url="http://localhost:1"))
        with pytest.raises(RuntimeError, match="not reachable"):
            await provider.chat(
                messages=[ChatMessage(role="user", content="Hi")],
                model="llama3",
            )

    def test_supports_streaming(self):
        provider = OllamaProvider()
        assert provider.supports_streaming is True


# ============================================================================
# Provider Factory Tests
# ============================================================================

class TestProviderFactory:
    def test_register_and_get(self):
        from app.providers.factory import ProviderFactory
        ProviderFactory.clear()

        mock_provider = MagicMock()
        mock_provider.is_configured = True
        ProviderFactory.register("test", mock_provider)

        assert ProviderFactory.get("test") is mock_provider

    def test_get_returns_none_for_unknown(self):
        from app.providers.factory import ProviderFactory
        assert ProviderFactory.get("nonexistent") is None

    def test_list_configured(self):
        from app.providers.factory import ProviderFactory
        ProviderFactory.clear()

        mock1 = MagicMock()
        mock1.is_configured = True
        mock2 = MagicMock()
        mock2.is_configured = False

        ProviderFactory.register("configured", mock1)
        ProviderFactory.register("unconfigured", mock2)

        configured = ProviderFactory.list_configured()
        assert "configured" in configured
        assert "unconfigured" not in configured

    def test_clear(self):
        from app.providers.factory import ProviderFactory
        mock = MagicMock()
        ProviderFactory.register("test", mock)
        ProviderFactory.clear()
        assert ProviderFactory.get("test") is None

    def test_get_for_model(self):
        from app.providers.factory import ProviderFactory
        ProviderFactory.clear()

        mock_provider = MagicMock()
        mock_provider.is_configured = True
        ProviderFactory.register("openai", mock_provider)

        result = ProviderFactory.get_for_model("gpt-4")
        assert result is mock_provider

    def test_get_for_model_unknown(self):
        from app.providers.factory import ProviderFactory
        result = ProviderFactory.get_for_model("nonexistent")
        assert result is None
