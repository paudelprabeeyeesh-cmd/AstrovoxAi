"""AI Agent system — autonomous multi-step reasoning and task execution."""

import logging
import time
import re
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

from .providers.base import AIProvider, ChatMessage, ChatResponse
from .providers.factory import ProviderFactory
from .providers.models import get_model_info, get_provider_for_model
from .memory_manager import memory_manager
from .knowledge_base import knowledge_base

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent execution state."""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentStep:
    """A single step in an agent's plan."""
    step_number: int
    action: str
    description: str
    status: str = "pending"  # pending, running, completed, failed
    result: str = ""
    tool_used: str = ""
    parameters: dict = field(default_factory=dict)


@dataclass
class AgentTask:
    """An agent task with multi-step plan."""
    id: str
    user_id: str
    goal: str
    state: AgentState = AgentState.IDLE
    steps: list[AgentStep] = field(default_factory=list)
    current_step: int = 0
    result: str = ""
    created_at: float = 0.0
    completed_at: float = 0.0
    metadata: dict = field(default_factory=dict)


class ToolRegistry:
    """Registry of available tools for the agent."""

    def __init__(self):
        self._tools: dict[str, callable] = {}

    def register(self, name: str, func, description: str = ""):
        """Register a tool."""
        self._tools[name] = {"func": func, "description": description}

    def get(self, name: str) -> Optional[dict]:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        """List all available tools."""
        return [
            {"name": name, "description": info["description"]}
            for name, info in self._tools.items()
        ]

    async def execute(self, name: str, **kwargs) -> str:
        """Execute a tool."""
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found"

        try:
            result = await tool["func"](**kwargs)
            return str(result)
        except Exception as e:
            return f"Error executing {name}: {str(e)}"


class AIAgent:
    """Autonomous AI agent with multi-step reasoning."""

    def __init__(self, user_id: str, provider: Optional[AIProvider] = None):
        self.user_id = user_id
        self.provider = provider
        self.tools = ToolRegistry()
        self._tasks: dict[str, AgentTask] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Register default tools."""
        self.tools.register(
            "search_memory",
            self._tool_search_memory,
            "Search user's memory for relevant information",
        )
        self.tools.register(
            "search_knowledge",
            self._tool_search_knowledge,
            "Search the knowledge base for documents",
        )
        self.tools.register(
            "save_memory",
            self._tool_save_memory,
            "Save information to user's memory",
        )
        self.tools.register(
            "summarize",
            self._tool_summarize,
            "Summarize text content",
        )
        self.tools.register(
            "calculate",
            self._tool_calculate,
            "Perform mathematical calculations",
        )
        self.tools.register(
            "get_time",
            self._tool_get_time,
            "Get current date and time",
        )

    async def _tool_search_memory(self, query: str) -> str:
        results = await memory_manager.search_memories(self.user_id, query)
        if not results:
            return "No relevant memories found"
        return "\n".join(f"- {r.entry.content}" for r in results[:5])

    async def _tool_search_knowledge(self, query: str) -> str:
        results = await knowledge_base.search(self.user_id, query)
        if not results:
            return "No relevant documents found"
        return "\n".join(f"- {r.chunk.content[:200]}" for r in results[:3])

    async def _tool_save_memory(self, content: str) -> str:
        await memory_manager.save_memory(self.user_id, content, importance=2)
        return "Memory saved successfully"

    async def _tool_summarize(self, text: str) -> str:
        if len(text) < 200:
            return text
        return text[:500] + "..."

    async def _tool_calculate(self, expression: str) -> str:
        import ast
        import operator
        try:
            node = ast.parse(expression.strip(), mode='eval')
            allowed_ops = (
                ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
                ast.FloorDiv, ast.USub, ast.UAdd,
            )
            allowed_funcs = {'abs', 'round', 'min', 'max', 'sum'}
            for n in ast.walk(node):
                if isinstance(n, ast.BinOp) and not isinstance(n.op, allowed_ops):
                    return "Unsupported operator"
                if isinstance(n, ast.UnaryOp) and not isinstance(n.op, allowed_ops):
                    return "Unsupported operator"
                if isinstance(n, ast.Call):
                    if isinstance(n.func, ast.Name) and n.func.id not in allowed_funcs:
                        return f"Unsupported function: {n.func.id}"
                if isinstance(n, (ast.Name, ast.Attribute, ast.Subscript)):
                    return "Variables not allowed"
            result = eval(compile(node, '<string>', 'eval'), {"__builtins__": {}}, {})
            return str(result)
        except Exception as e:
            return f"Calculation error: {str(e)}"

    async def _tool_get_time(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _get_provider(self) -> AIProvider:
        """Get the AI provider for this agent."""
        if self.provider:
            return self.provider

        configured = ProviderFactory.list_configured()
        if configured:
            provider = ProviderFactory.get(configured[0])
            if provider:
                return provider

        raise RuntimeError("No AI provider configured")

    async def create_task(self, goal: str) -> AgentTask:
        """Create a new agent task with a plan."""
        import uuid

        task = AgentTask(
            id=str(uuid.uuid4())[:8],
            user_id=self.user_id,
            goal=goal,
            state=AgentState.PLANNING,
            created_at=time.time(),
        )

        plan = await self._create_plan(goal)
        task.steps = plan
        task.state = AgentState.EXECUTING
        self._tasks[task.id] = task

        return task

    async def _create_plan(self, goal: str) -> list[AgentStep]:
        """Create an execution plan for a goal."""
        provider = self._get_provider()

        system_prompt = (
            "You are an AI planning assistant. Given a goal, break it down into "
            "3-5 concrete steps. Each step should have an action and description. "
            "Format each step on a new line as: ACTION: description"
        )

        messages = [ChatMessage(role="user", content=f"Goal: {goal}")]

        try:
            model_info = get_model_info("gpt-4")
            model = model_info.id if model_info else "gpt-4"

            response = await provider.chat(
                messages=messages,
                model=model,
                system_prompt=system_prompt,
                max_tokens=500,
            )

            steps = []
            for i, line in enumerate(response.content.strip().split("\n"), 1):
                line = line.strip()
                if not line:
                    continue

                if ":" in line:
                    action, description = line.split(":", 1)
                    steps.append(AgentStep(
                        step_number=i,
                        action=action.strip(),
                        description=description.strip(),
                    ))
                else:
                    steps.append(AgentStep(
                        step_number=i,
                        action=f"step_{i}",
                        description=line,
                    ))

            if not steps:
                steps = [AgentStep(step_number=1, action="execute", description=goal)]

            return steps

        except Exception as e:
            logger.error(f"Failed to create plan: {e}")
            return [AgentStep(step_number=1, action="execute", description=goal)]

    async def execute_task(self, task_id: str) -> AgentTask:
        """Execute an agent task."""
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        provider = self._get_provider()
        task.state = AgentState.EXECUTING

        for i, step in enumerate(task.steps):
            task.current_step = i
            step.status = "running"

            try:
                result = await self._execute_step(step, provider)
                step.result = result
                step.status = "completed"
            except Exception as e:
                step.result = f"Error: {str(e)}"
                step.status = "failed"
                task.state = AgentState.FAILED
                return task

        task.state = AgentState.COMPLETED
        task.completed_at = time.time()
        task.result = "\n".join(
            f"Step {s.step_number}: {s.result}" for s in task.steps
        )

        return task

    async def _execute_step(self, step: AgentStep, provider: AIProvider) -> str:
        """Execute a single step."""
        system_prompt = (
            f"You are executing step {step.step_number}: {step.description}. "
            f"Use available tools if needed. Be concise and direct."
        )

        messages = [ChatMessage(role="user", content=step.description)]

        model_info = get_model_info("gpt-4")
        model = model_info.id if model_info else "gpt-4"

        response = await provider.chat(
            messages=messages,
            model=model,
            system_prompt=system_prompt,
            max_tokens=1000,
        )

        return response.content

    def get_task(self, task_id: str) -> Optional[AgentTask]:
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[AgentTask]:
        return list(self._tasks.values())


class AgentManager:
    """Manage AI agents for multiple users."""

    def __init__(self):
        self._agents: dict[str, AIAgent] = {}

    def get_agent(self, user_id: str) -> AIAgent:
        """Get or create an agent for a user."""
        if user_id not in self._agents:
            self._agents[user_id] = AIAgent(user_id)
        return self._agents[user_id]

    def remove_agent(self, user_id: str):
        self._agents.pop(user_id, None)


agent_manager = AgentManager()
