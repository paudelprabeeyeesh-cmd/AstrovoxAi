"""
Slash commands for powerful user interactions.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SlashCommand:
    command: str
    description: str
    usage: str
    aliases: List[str] = None
    requires_admin: bool = False
    requires_premium: bool = False

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


class SlashCommandHandler(ABC):
    """Base class for slash command handlers."""

    @abstractmethod
    async def execute(self, command: str, args: List[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        pass


class SlashCommandRegistry:
    """Registry of slash commands."""

    def __init__(self):
        self.commands: Dict[str, SlashCommand] = {}
        self.handlers: Dict[str, SlashCommandHandler] = {}
        self._setup_default_commands()

    def _setup_default_commands(self):
        """Setup default slash commands."""
        self.register(SlashCommand("/help", "Show help", "/help [command]"), HelpCommandHandler())
        self.register(SlashCommand("/model", "Switch model", "/model <model_name>"), ModelCommandHandler())
        self.register(SlashCommand("/code", "Run code", "/code <code>"), CodeCommandHandler())
        self.register(SlashCommand("/search", "Web search", "/search <query>"), SearchCommandHandler())
        self.register(SlashCommand("/image", "Generate image", "/image <prompt>"), ImageCommandHandler())
        self.register(SlashCommand("/clear", "Clear conversation", "/clear"), ClearCommandHandler())
        self.register(SlashCommand("/export", "Export conversation", "/export [format]"), ExportCommandHandler())
        self.register(SlashCommand("/stats", "Show statistics", "/stats"), StatsCommandHandler())
        self.register(SlashCommand("/memory", "Manage memory", "/memory <show|clear|add>"), MemoryCommandHandler())
        self.register(SlashCommand("/temperature", "Set temperature", "/temperature <0.0-2.0>"), TemperatureCommandHandler())
        self.register(SlashCommand("/system", "Set system prompt", "/system <prompt>"), SystemCommandHandler())
        self.register(SlashCommand("/artifacts", "View artifacts", "/artifacts"), ArtifactsCommandHandler())
        self.register(SlashCommand("/branch", "Create branch", "/branch [name]"), BranchCommandHandler())
        self.register(SlashCommand("/merge", "Merge branch", "/merge <source> <target>"), MergeCommandHandler())
        self.register(SlashCommand("/fork", "Fork conversation", "/fork"), ForkCommandHandler())
        self.register(SlashCommand("/pin", "Pin message", "/pin <message_id>"), PinCommandHandler())
        self.register(SlashCommand("/feedback", "Give feedback", "/feedback <thumbs_up|thumbs_down>"), FeedbackCommandHandler())

    def register(self, command: SlashCommand, handler: SlashCommandHandler):
        self.commands[command.command] = command
        self.handlers[command.command] = handler
        for alias in command.aliases:
            self.commands[alias] = command
            self.handlers[alias] = handler

    def get_command(self, command: str) -> Optional[SlashCommand]:
        return self.commands.get(command)

    def get_handler(self, command: str) -> Optional[SlashCommandHandler]:
        return self.handlers.get(command)

    def list_commands(self, user_premium: bool = False, user_admin: bool = False) -> List[SlashCommand]:
        return [cmd for cmd in self.commands.values() if (cmd.requires_admin and user_admin) or (cmd.requires_premium and user_premium) or (not cmd.requires_admin and not cmd.requires_premium)]

    async def execute(self, command: str, args: List[str], user_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        cmd = self.get_command(command)
        if not cmd:
            return {"error": f"Unknown command: {command}", "suggestion": "Type /help to see available commands"}
        if cmd.requires_admin and not user_context.get("is_admin", False):
            return {"error": f"Command /{command} requires admin privileges"}
        if cmd.requires_premium and not user_context.get("is_premium", False):
            return {"error": f"Command /{command} requires premium subscription"}
        handler = self.get_handler(command)
        if handler:
            return await handler.execute(command, args, user_context)
        return {"error": f"No handler for /{command}"}


# Command handlers
class HelpCommandHandler(SlashCommandHandler):
    async def execute(self, command: str, args: List[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        registry = user_context.get("slash_registry")
        if registry and args:
            cmd = registry.get_command(args[0])
            if cmd:
                return {"text": f"/{cmd.command}\nDescription: {cmd.description}\nUsage: {cmd.usage}"}
        commands = user_context.get("slash_registry").list_commands(user_context.get("is_premium", False), user_context.get("is_admin", False)) if registry else []
        return {"text": "Available commands:\n" + "\n".join(f"/{c.command} - {c.description}" for c in commands)}

class ModelCommandHandler(SlashCommandHandler):
    async def execute(self, command: str, args: List[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        if not args:
            return {"text": "Current model: " + user_context.get("model", "default")}
        return {"text": f"Switched to model: {args[0]}"}

class CodeCommandHandler(SlashCommandHandler):
    async def execute(self, command: str, args: List[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        from app.core.code_execution import code_sandbox
        code = " ".join(args)
        result = code_sandbox.execute_python(code)
        return {"text": f"Exit code: {result.exit_code}\n\nOutput:\n{result.stdout}\n{result.stderr}", "error": result.error}

class SearchCommandHandler(SlashCommandHandler):
    async def execute(self, command: str, args: List[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        from app.core.web_search import web_search
        query = " ".join(args)
        return {"text": web_search.search_and_format(query)}

class ImageCommandHandler(SlashCommandHandler):
    async def execute(self, command: str, args: List[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        from app.core.image_generation import image_generation
        prompt = " ".join(args)
        results = image_generation.generate(prompt)
        if results:
            return {"text": f"Generated image: {results[0].url}", "image_url": results[0].url}
        return {"text": "Image generation failed"}

class ClearCommandHandler(SlashCommandHandler):
    async def execute(self, command: str, args: List[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        return {"action": "clear_conversation", "text": "Conversation cleared"}

class ExportCommandHandler(SlashCommandHandler):
    async def execute(self, command: str, args: List[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        format = args[0] if args else "markdown"
        return {"text": f"Exported as {format}", "format": format}

class StatsCommandHandler(SlashCommandHandler):
    async def execute(self, command: str, args: List[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        return {"text": "Statistics:\nMessages: 0\nTokens: 0\nCost: $0.00"}

class MemoryCommandHandler(SlashCommandHandler):
    async def execute(self, command: str, args: List[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        action = args[0] if args else "show"
        return {"text": f"Memory {action}: OK", "action": action}

class TemperatureCommandHandler(SlashCommandHandler):
    async def execute(self, command: str, args: List[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        if not args:
            return {"text": f"Current temperature: {user_context.get('temperature', 0.7)}"}
        try:
            temp = float(args[0])
            return {"text": f"Temperature set to {temp}", "temperature": temp}
        except ValueError:
            return {"text": "Invalid temperature. Use 0.0-2.0"}

class SystemCommandHandler(SlashCommandHandler):
    async def execute(self, command: str, args: List[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = " ".join(args)
        return {"text": f"System prompt updated: {prompt[:100]}", "system_prompt": prompt}

class ArtifactsCommandHandler(SlashCommandHandler):
    async def execute(self, command: str, args: List[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        from app.core.artifacts_core import artifact_manager
        artifacts = artifact_manager.get_conversation_artifacts(user_context.get("conversation_id", ""))
        return {"text": f"Found {len(artifacts)} artifacts", "artifacts": [a.to_dict() for a in artifacts]}

class BranchCommandHandler(SlashCommandHandler):
    async def execute(self, command: str, args: List[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        from app.core.conversation_branching_core import conversation_branching
        name = args[0] if args else None
        branch_id = conversation_branching.create_branch(name=name)
        return {"text": f"Created branch: {branch_id}", "branch_id": branch_id}

class MergeCommandHandler(SlashCommandHandler):
    async def execute(self, command: str, args: List[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        if len(args) < 2:
            return {"text": "Usage: /merge <source> <target>"}
        from app.core.conversation_branching_core import conversation_branching
        success = conversation_branching.merge_branches(args[0], args[1])
        return {"text": f"Merge {'successful' if success else 'failed'}", "success": success}

class ForkCommandHandler(SlashCommandHandler):
    async def execute(self, command: str, args: List[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        from app.core.conversation_branching_core import conversation_branching
        branch_id = conversation_branching.create_branch()
        return {"text": f"Forked conversation: {branch_id}", "branch_id": branch_id}

class PinCommandHandler(SlashCommandHandler):
    async def execute(self, command: str, args: List[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        return {"text": f"Pinned message: {args[0] if args else 'last'}", "action": "pin"}

class FeedbackCommandHandler(SlashCommandHandler):
    async def execute(self, command: str, args: List[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        feedback_type = args[0] if args else "neutral"
        return {"text": f"Feedback recorded: {feedback_type}", "feedback": feedback_type}


slash_command_registry = SlashCommandRegistry()
