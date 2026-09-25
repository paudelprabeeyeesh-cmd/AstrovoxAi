import pytest
import asyncio
from app.core.streaming_core import streaming_manager, StreamEventType
from app.core.code_execution import code_sandbox
from app.core.web_search import web_search
from app.core.image_generation import ImageGenerationEngine, ImageUnderstandingEngine
from app.core.artifacts_core import artifact_manager, ArtifactType
from app.core.conversation_history import conversation_history, ConversationHistoryManager
from app.core.slash_commands import slash_command_registry, SlashCommandRegistry
from app.core.custom_instructions import instruction_manager, preferences_manager, CustomInstructionManager, UserPreferencesManager
from app.core.feedback_system import feedback_collector, typing_indicator_manager, FeedbackCollector, TypingIndicatorManager, FeedbackType, FeedbackCategory


class TestStreaming:
    def test_stream_manager_exists(self):
        assert streaming_manager is not None

    def test_create_sse_response(self):
        async def fake_gen():
            yield "token1"
            yield "token2"
        response = streaming_manager.create_sse_response("stream1", fake_gen())
        assert response is not None


class TestCodeExecution:
    def test_execute_python_print(self):
        result = code_sandbox.execute_python("print('hello')")
        assert result.exit_code == 0
        assert "hello" in result.stdout

    def test_execute_python_math(self):
        result = code_sandbox.execute_python("x = 2 + 2\nprint(x)")
        assert result.exit_code == 0
        assert "4" in result.stdout

    def test_execute_python_timeout(self):
        result = code_sandbox.execute_python("import time\ntime.sleep(100)", timeout=1.0)
        assert result.error == "Timeout"

    def test_validate_blocked_import(self):
        warnings = code_sandbox.validate_python_code("import subprocess")
        assert len(warnings) > 0


class TestWebSearch:
    def test_search_returns_list(self):
        results = web_search.search("test query", max_results=3)
        assert isinstance(results, list)

    def test_search_and_format(self):
        formatted = web_search.search_and_format("test", max_results=2)
        assert isinstance(formatted, str)


class TestImageGeneration:
    def test_generate_returns_list(self):
        engine = ImageGenerationEngine()
        results = engine.generate("a red apple", n=1)
        assert isinstance(results, list)

    def test_analyze_returns_string(self):
        understanding = ImageUnderstandingEngine()
        result = understanding.analyze("https://example.com/image.jpg", "describe")
        assert isinstance(result, str)


class TestArtifacts:
    def test_create_code_artifact(self):
        artifact = artifact_manager.create_code_artifact("print('hello')", "python", "Test Code")
        assert artifact.type == ArtifactType.CODE
        assert artifact.language == "python"

    def test_create_and_get_artifact(self):
        art = artifact_manager.create_artifact(ArtifactType.MARKDOWN, "Title", "# Hello", language="markdown")
        retrieved = artifact_manager.get_artifact(art.artifact_id)
        assert retrieved is not None
        assert retrieved.title == "Title"

    def test_update_artifact(self):
        art = artifact_manager.create_artifact(ArtifactType.CODE, "Old", "old code", language="python")
        updated = artifact_manager.update_artifact(art.artifact_id, "new code", title="New")
        assert updated.title == "New"
        assert updated.content == "new code"


class TestConversationHistory:
    def test_create_and_add_message(self):
        conv = conversation_history.create_conversation("user1", "Test")
        msg = conversation_history.add_message(conv.conversation_id, "user", "hello")
        assert msg.content == "hello"
        assert len(conv.messages) == 1

    def test_get_user_conversations(self):
        convs = conversation_history.get_user_conversations("user1")
        assert isinstance(convs, list)

    def test_search_messages(self):
        conv = conversation_history.create_conversation("user1", "Test")
        conversation_history.add_message(conv.conversation_id, "user", "python code example")
        results = conv.search_messages("python")
        assert len(results) > 0


class TestSlashCommands:
    def test_register_command(self):
        registry = SlashCommandRegistry()
        from app.core.slash_commands import SlashCommand, SlashCommandHandler
        class TestHandler(SlashCommandHandler):
            async def execute(self, command, args, user_context):
                return {"text": "test"}
        registry.register(SlashCommand("/test", "Test", "/test"), TestHandler())
        assert registry.get_command("/test") is not None

    def test_help_command(self):
        result = asyncio.run(slash_command_registry.execute("/help", [], {"is_admin": False, "is_premium": False}))
        assert "text" in result

    def test_model_command(self):
        result = asyncio.run(slash_command_registry.execute("/model", [], {"is_admin": False, "is_premium": False}))
        assert "text" in result

    def test_code_command(self):
        result = asyncio.run(slash_command_registry.execute("/code", ["print(1+1)"], {"is_admin": False, "is_premium": False}))
        assert "text" in result


class TestCustomInstructions:
    def test_add_and_get_instruction(self):
        instruction = instruction_manager.add_instruction("user1", "Be concise", category="style")
        assert instruction.content == "Be concise"
        instructions = instruction_manager.get_user_instructions("user1")
        assert len(instructions) > 0

    def test_preferences_manager(self):
        prefs = preferences_manager.get_preferences("user1")
        assert prefs.user_id == "user1"
        updated = preferences_manager.update_preferences("user1", temperature=0.9)
        assert updated.temperature == 0.9


class TestFeedback:
    def test_submit_feedback(self):
        feedback = feedback_collector.submit_feedback("user1", "msg1", "conv1", FeedbackType.THUMBS_UP, FeedbackCategory.QUALITY)
        assert feedback.feedback_type == FeedbackType.THUMBS_UP
        stats = feedback_collector.get_feedback_stats()
        assert stats["total"] > 0

    def test_typing_indicator(self):
        typing_indicator_manager.start_typing("conv1", "user1")
        assert typing_indicator_manager.is_typing("conv1")
        typing_indicator_manager.stop_typing("conv1")
        assert not typing_indicator_manager.is_typing("conv1")
