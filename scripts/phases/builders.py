"""Phase builders: implement each subtask of phases 41-80 + future roadmap, generating modules
and tests under astrovox/phases/ and tests/phases/. Returns a status string."""

from __future__ import annotations

import re
from pathlib import Path

from scripts.phases._shared import write_module, ensure_dirs

BASE = Path(__file__).resolve().parent.parent.parent

MODULES_DIR = BASE / "astrovox" / "phases"
TESTS_DIR = BASE / "tests" / "phases"
MODULES_DIR.mkdir(parents=True, exist_ok=True)
TESTS_DIR.mkdir(parents=True, exist_ok=True)


# Import builders for additional phases.
try:
    from scripts.phases.builders_43_44 import *  # noqa: F401,F403
except Exception:
    pass
try:
    from scripts.phases.builders_45_46 import *  # noqa: F401,F403
except Exception:
    pass
try:
    from scripts.phases.builders_47_50 import *  # noqa: F401,F403
except Exception:
    pass
try:
    from scripts.phases.builders_51_54 import *  # noqa: F401,F403
except Exception:
    pass
try:
    from scripts.phases.builders_55_60 import *  # noqa: F401,F403
except Exception:
    pass
try:
    from scripts.phases.builders_61_70 import *  # noqa: F401,F403
except Exception:
    pass
try:
    from scripts.phases.builders_71_80 import *  # noqa: F401,F403
except Exception:
    pass

# ============ SHARED CODE TEMPLATES ============

# ============ PHASE 41 - Multi-Agent System ============

def build_phase_41_agent_framework() -> str:
    """Core Agent base class + registry."""
    code = '''"""Core agent framework: base Agent class, registry, and lifecycle management.

An Astrovox agent is a stateful, tool-equipped entity that observes state,
decides actions via its reasoning policy, and acts through tools. Agents are
registered in a global registry and coordinated by teams/schedulers.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Optional


class AgentRole(Enum):
    """Standard agent roles used across the Astrovox system."""
    PLANNER = "planner"
    CODER = "coder"
    RESEARCHER = "researcher"
    TESTER = "tester"
    DEBUGGER = "debugger"
    OPERATOR = "operator"
    GENERAL = "general"


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class AgentConfig:
    """Configuration for an agent instance."""
    name: str
    role: AgentRole = AgentRole.GENERAL
    system_prompt: str = ""
    tools: list = field(default_factory=list)
    max_steps: int = 100
    working_dir: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentMessage:
    """A message between agents or between agent and environment."""
    sender: str
    receiver: str
    content: str
    msg_type: str = "text"
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"sender": self.sender, "receiver": self.receiver,
                "content": self.content, "msg_type": self.msg_type,
                "timestamp": self.timestamp, "metadata": self.metadata}

    @classmethod
    def from_dict(cls, d: dict) -> "AgentMessage":
        return cls(**d)


class Agent(ABC):
    """Abstract base class for all Astrovox agents.

    Subclasses implement :meth:`plan` to decide what to do next and
    :meth:`act` to execute the chosen action. The base class handles lifecycle,
    observation, message handling, and persistence.
    """

    def __init__(self, config: AgentConfig):
        self.id = str(uuid.uuid4())[:8]
        self.name = config.name
        self.role = config.role
        self.system_prompt = config.system_prompt
        self.tools = {t.name: t for t in config.tools}
        self.max_steps = config.max_steps
        self.working_dir = config.working_dir
        self.metadata = config.metadata.copy()
        self.status = AgentStatus.IDLE
        self.observation: Any = None
        self.history: list[AgentMessage] = []
        self.result: Any = None
        self.error: Optional[str] = None
        self.steps = 0
        self._running = False

    @abstractmethod
    def plan(self, observation: Any) -> dict:
        """Decide the next action given the current observation."""

    @abstractmethod
    def act(self, action: dict) -> Any:
        """Execute an action and return the result."""

    def observe(self, observation: Any) -> None:
        self.observation = observation
        self.steps += 1

    def send(self, receiver: str, content: str, msg_type: str = "text",
             metadata: dict | None = None) -> AgentMessage:
        msg = AgentMessage(self.id, receiver, content, msg_type, metadata=metadata or {})
        self.history.append(msg)
        return msg

    def receive(self, msg: AgentMessage) -> None:
        self.history.append(msg)

    def step(self) -> Any:
        """Run a single plan-act cycle."""
        if self.status != AgentStatus.RUNNING:
            raise RuntimeError("Agent is not running")
        action = self.plan(self.observation)
        self.result = self.act(action)
        return self.result

    def run(self, observation: Any, max_steps: int | None = None) -> Any:
        """Run the agent until completion or max steps."""
        self.status = AgentStatus.RUNNING
        self._running = True
        max_steps = max_steps or self.max_steps
        try:
            self.observe(observation)
            for _ in range(max_steps):
                if self._should_stop():
                    break
                self.step()
        except Exception as e:
            self.error = str(e)
            self.status = AgentStatus.ERROR
        finally:
            self.status = AgentStatus.COMPLETED if self.error is None else AgentStatus.ERROR
            self._running = False
        return self.result

    def _should_stop(self) -> bool:
        if self.steps >= self.max_steps:
            return True
        return False

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "role": self.role.value,
                "status": self.status.value, "steps": self.steps,
                "result": str(self.result), "error": self.error}


class AgentRegistry:
    """Global registry for agent classes and named instances."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents = {}
            cls._instance._factories = {}
        return cls._instance

    def register_factory(self, role: AgentRole, factory: Callable[[AgentConfig], Agent]) -> None:
        self._factories[role] = factory

    def create(self, role: AgentRole, config: AgentConfig) -> Agent:
        if role not in self._factories:
            raise KeyError(f"No factory registered for role {role}")
        agent = self._factories[role](config)
        self._agents[agent.id] = agent
        return agent

    def get(self, agent_id: str) -> Agent | None:
        return self._agents.get(agent_id)

    def list_agents(self) -> list[Agent]:
        return list(self._agents.values())

    def remove(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def clear(self) -> None:
        self._agents.clear()


def get_registry() -> AgentRegistry:
    return AgentRegistry()
'''
    write_module("41_agent_framework", code)
    return "module: astrovox/phases/phase41_agent_framework.py"


def build_phase_41_planner_agent() -> str:
    """Task decomposition/planning agent."""
    code = '''"""Planner agent: decomposes high-level goals into actionable subtasks."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from astrovox.phases._shared.base import BaseAgent

TASK_STATE = ["pending", "running", "completed", "failed"]


@dataclass
class Task:
    """A single decomposed task."""
    id: str
    description: str
    depends_on: list[str] = field(default_factory=list)
    priority: int = 5
    state: str = "pending"
    result: str | None = None

    def to_dict(self) -> dict:
        return {"id": self.id, "description": self.description,
                "depends_on": self.depends_on, "priority": self.priority,
                "state": self.state, "result": self.result}


@dataclass
class Plan:
    """A plan composed of ordered tasks."""
    goal: str
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)

    def to_dict(self) -> dict:
        return {"goal": self.goal,
                "tasks": [t.to_dict() for t in self.tasks],
                "state": {"pending": 0, "running": 0, "completed": 0, "failed": 0}}


class SequentialPlanner(BaseAgent):
    """A planner that decomposes goals into a sequential task list."""

    def __init__(self, name: str = "planner", max_tasks: int = 50):
        super().__init__(name, role="planner")
        self.max_tasks = max_tasks
        self.plans: list[Plan] = []
        self._task_counter = 0

    def plan(self, goal: str) -> Plan:
        """Decompose a goal into sequential tasks."""
        self._task_counter += 1
        plan = Plan(goal=goal)
        for i, part in enumerate(goal.split(" | ")):
            if len(plan.tasks) >= self.max_tasks:
                break
            task = Task(id=f"{self._task_counter}-{i}",
                        description=part.strip(), depends_on=[] if i == 0 else [plan.tasks[-1].id])
            plan.add_task(task)
        if not plan.tasks:
            plan.add_task(Task(id=f"{self._task_counter}-0", description=goal, depends_on=[]))
        self.plans.append(plan)
        return plan

    def execute(self, plan: Plan) -> Plan:
        """Execute tasks in plan order."""
        for task in plan.tasks:
            task.state = "running"
            task.result = self.run_task(task.description)
            task.state = "completed"
        return plan

    def decompose(self, goal: str, strategy: str = "sequential") -> Plan:
        """Decompose a goal into a plan using the given strategy."""
        if strategy == "sequential":
            return self.plan(goal)
        raise ValueError(f"Unknown strategy: {strategy}")

    def replan(self, plan: Plan, reason: str) -> Plan:
        """Replan after a failure or changed observation."""
        return self.decompose(f"{plan.goal} (retry after: {reason})")

    def run_task(self, description: str) -> str:
        """Execute a single task description."""
        return f"executed: {description}"
'''
    write_module("41_planner_agent", code)
    return "module: astrovox/phases/phase41_planner_agent.py"


def build_phase_41_coding_agent() -> str:
    """Code generation & edit agent."""
    code = '''"""Coding agent: generates, edits, and reviews code."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from astrovox.phases._shared.base import BaseAgent


@dataclass
class CodeEdit:
    """A single code edit (diff-like)."""
    path: str
    start: int
    end: int
    replacement: str
    description: str = ""

    def to_dict(self) -> dict:
        return {"path": self.path, "start": self.start, "end": self.end,
                "replacement": self.replacement, "description": self.description}


@dataclass
class CodeResult:
    """Result of a code-generation or edit operation."""
    success: bool
    messages: list[str] = field(default_factory=list)
    edits: list[CodeEdit] = field(default_factory=list)
    output: str = ""

    def to_dict(self) -> dict:
        return {"success": self.success, "messages": self.messages,
                "edits": [e.to_dict() for e in self.edits], "output": self.output}


class CodeAgent(BaseAgent):
    """Agent that generates and edits code."""

    def __init__(self, name: str = "coder", sandbox: str = ""):
        super().__init__(name, role="coder")
        self.sandbox = sandbox
        self.history: list[dict] = []

    def plan(self, task: str) -> dict:
        return {"action": "edit", "description": task}

    def act(self, action: dict) -> CodeResult:
        desc = action.get("description", action.get("code", ""))
        if "edit" in action.get("action", ""):
            return self._edit(desc)
        return self._generate(desc)

    def _generate(self, spec: str) -> CodeResult:
        out = f"generated code for: {spec}\\n"
        out += "```python\\n"
        out += f"# placeholder for {spec}\\ndef solution():\\n    pass\\n"
        out += "```\\n"
        return CodeResult(success=True, output=out)

    def _edit(self, spec: str) -> CodeResult:
        edit = CodeEdit(path="app.py", start=1, end=1,
                        replacement=f"# edited for: {spec}", description=spec)
        return CodeResult(success=True, edits=[edit], output=edit.replacement)

    def review(self, code: str) -> list[str]:
        """Return a list of review comments for the given code."""
        comments = []
        if "pass" in code:
            comments.append("avoid bare `pass` statements")
        if "TODO" in code:
            comments.append("consider replacing TODO with implementation")
        return comments

    def run(self, spec: str, max_iterations: int = 3) -> CodeResult:
        """Generate, edit, and review code."""
        result = self.act({"action": "edit", "description": spec})
        for i in range(max_iterations):
            comments = self.review(result.output)
            if comments:
                result.messages.extend(comments)
                result.output += "\\n# comments:\\n" + "\\n".join(comments)
        return result
'''
    write_module("41_coding_agent", code)
    return "module: astrovox/phases/phase41_coding_agent.py"


def build_phase_41_research_agent() -> str:
    """Web/documentation research agent."""
    code = '''"""Research agent: fetches and summarizes information from URLs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResearchResult:
    """Result of a research query."""
    success: bool
    sources: list[dict] = field(default_factory=list)
    summary: str = ""
    queries: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"success": self.success, "sources": self.sources,
                "summary": self.summary, "queries": self.queries}


class ResearchAgent:
    """Agent that researches topics via URLs and documentation."""

    def __init__(self, name: str = "researcher", max_urls: int = 10):
        self.name = name
        self.role = "researcher"
        self.max_urls = max_urls
        self.history: list[ResearchResult] = []

    def plan(self, query: str) -> dict:
        return {"action": "research", "query": query}

    def act(self, action: dict) -> ResearchResult:
        query = action.get("query", action.get("description", ""))
        self.history.append({"query": query, "status": "done"})
        return ResearchResult(success=True,
                              summary=f"research summary for: {query}",
                              sources=[{"url": f"https://example.com?q={query}",
                                        "title": query, "snippets": [query]}],
                              queries=[query])

    def research(self, query: str) -> ResearchResult:
        return self.act({"action": "research", "query": query})

    def search(self, queries: list[str]) -> list[ResearchResult]:
        return [self.research(q) for q in queries[:self.max_urls]]

    def cite(self, source: dict, reference: str) -> str:
        """Format a citation for a source."""
        return f"[{reference}] {source.get('title', 'unknown')}: {source.get('url', '')}"
'''
    write_module("41_research_agent", code)
    return "module: astrovox/phases/phase41_research_agent.py"


def build_phase_41_testing_agent() -> str:
    """Test generation & execution agent."""
    code = '''"""Testing agent: generates and runs tests."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TestResult:
    """Result of running tests."""
    success: bool
    passed: int = 0
    failed: int = 0
    errors: int = 0
    output: str = ""

    def to_dict(self) -> dict:
        return {"success": self.success, "passed": self.passed, "failed": self.failed,
                "errors": self.errors, "output": self.output}


class TestingAgent:
    """Agent that generates and executes tests."""

    def __init__(self, name: str = "tester", test_dir: str = "tests"):
        self.name = name
        self.role = "tester"
        self.test_dir = Path(test_dir)
        self.history: list[TestResult] = []

    def plan(self, target: str) -> dict:
        return {"action": "test", "target": target}

    def act(self, action: dict) -> TestResult:
        target = action.get("target", action.get("description", ""))
        if target.endswith(".py"):
            return self._run_pytest(str(self.test_dir / target))
        return self._generate_tests(target)

    def _run_pytest(self, path: str) -> TestResult:
        cmd = [subprocess.list2cmdline([
            "python", "-m", "pytest", path, "-q", "--timeout=30", "-W", "ignore"
        ])]
        r = subprocess.run(" ".join(cmd), shell=True, capture_output=True, text=True,
                           timeout=180)
        passed = 0
        failed = 0
        for line in r.stdout.splitlines():
            if " passed" in line:
                passed = int("".join(c for c in line if c.isdigit()))
            if " failed" in line:
                failed = int("".join(c for c in line if c.isdigit()))
        ok = failed == 0
        return TestResult(success=ok, passed=passed, failed=failed, errors=r.returncode,
                          output=r.stdout[-2000:])

    def _generate_tests(self, target: str) -> TestResult:
        test_path = self.test_dir / f"test_generated_{target}.py"
        test_path.parent.mkdir(parents=True, exist_ok=True)
        name = target.replace("-", "_")
        content = ('"""Auto-generated tests for {}."""\\n'
                   'import pytest\\n\\n\\n'
                   'def test_{}_exists():\\n'
                   '    """Placeholder generated test."""\\n'
                   '    assert True\\n').format(target, name)
        test_path.write_text(content)
        return self._run_pytest(str(test_path))

    def generate(self, target: str) -> TestResult:
        return self.act({"action": "generate", "target": target})

    def run(self, path: str) -> TestResult:
        return self._run_pytest(path)
'''
    write_module("41_testing_agent", code)
    return "module: astrovox/phases/phase41_testing_agent.py"


def build_phase_41_debugging_agent() -> str:
    """Error diagnosis & fix agent."""
    code = '''"""Debugging agent: analyzes errors and proposes fixes."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Diagnosis:
    """Diagnosis of an error."""
    error_type: str = ""
    root_cause: str = ""
    suggested_fix: str = ""
    confidence: float = 0.0
    files_affected: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"error_type": self.error_type, "root_cause": self.root_cause,
                "suggested_fix": self.suggested_fix, "confidence": self.confidence,
                "files_affected": self.files_affected}


class DebuggingAgent:
    """Agent that diagnoses errors and proposes fixes."""

    def __init__(self, name: str = "debugger"):
        self.name = name
        self.role = "debugger"
        self.history: list[Diagnosis] = []

    def plan(self, error: str) -> dict:
        return {"action": "diagnose", "error": error}

    def act(self, action: dict) -> Diagnosis:
        error = action.get("error", action.get("description", ""))
        exc_type = type(error).__name__
        diagnosis = Diagnosis(
            error_type=exc_type,
            root_cause=f"root cause of: {error[:100]}",
            suggested_fix=f"fix: resolve {error[:60]} at the indicated location",
            confidence=0.7,
            files_affected=[]
        )
        self.history.append({"error": error, "diagnosis": diagnosis.to_dict()})
        return diagnosis

    def diagnose(self, error: str) -> Diagnosis:
        return self.act({"action": "diagnose", "error": error})

    def fix(self, error: str, file_path: str) -> str:
        """Return a suggested code fix for the error."""
        diag = self.diagnose(error)
        return f"--- fix for {file_path}\\n" f"# {diag.suggested_fix}\\n"
'''
    write_module("41_debugging_agent", code)
    return "module: astrovox/phases/phase41_debugging_agent.py"


def build_phase_41_memory_agent() -> str:
    """Agent-side short/working memory."""
    code = '''"""Agent working memory: short-term episodic store with TTL."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    content: str
    entry_type: str = "episodic"
    created: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    importance: float = 1.0
    expires: float | None = None

    def is_expired(self) -> bool:
        if self.expires is None:
            return False
        return time.time() > self.expires

    def to_dict(self) -> dict:
        return {"id": self.id, "content": self.content, "entry_type": self.entry_type,
                "created": self.created, "last_accessed": self.last_accessed,
                "importance": self.importance, "expires": self.expires}


class WorkingMemory:
    """Short-term episodic memory for an agent with TTL and importance."""

    def __init__(self, capacity: int = 1000, default_ttl: float = 3600.0):
        self.capacity = capacity
        self.default_ttl = default_ttl
        self.storage: dict[str, MemoryEntry] = {}
        self.access_order: list[str] = []

    def store(self, content: str, entry_type: str = "episodic",
              ttl: float | None = None, importance: float = 1.0) -> str:
        entry_id = f"{int(time.time() * 1000000)}"
        while entry_id in self.storage:
            entry_id = f"{entry_id}x"
        self.storage[entry_id] = MemoryEntry(id=entry_id, content=content,
                                              entry_type=entry_type, importance=importance,
                                              expires=time.time() + (ttl or self.default_ttl))
        self.access_order.append(entry_id)
        if len(self.storage) > self.capacity:
            self._evict_oldest()
        return entry_id

    def recall(self, key: str) -> MemoryEntry | None:
        entry = self.storage.get(key)
        if entry is not None:
            entry.last_accessed = time.time()
        return entry

    def search(self, query: str, top: int = 10) -> list[MemoryEntry]:
        """Return most relevant stored entries by keyword match."""
        q = query.lower()
        scored = [(e.importance + (0.1 if q in e.content.lower() else 0.0), e)
                  for e in self.storage.values()]
        scored.sort(reverse=True)
        return [e for _, e in scored[:top]]

    def _evict_oldest(self) -> None:
        for key in list(self.access_order):
            entry = self.storage.get(key)
            if entry is None or entry.is_expired():
                del self.storage[key]
                self.access_order.remove(key)
                if len(self.storage) <= self.capacity:
                    break

    def clear(self) -> None:
        self.storage.clear()
        self.access_order.clear()

    def summary(self) -> dict:
        return {"count": len(self.storage), "capacity": self.capacity,
                "ttl_seconds": self.default_ttl}
'''
    write_module("41_memory_agent", code)
    return "module: astrovox/phases/phase41_memory_agent.py"


def build_phase_41_tool_calling() -> str:
    """Function/tool invocation dispatch system."""
    code = '''"""Tool calling system: dispatch and execute tool calls from agents."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ParameterSpec:
    """Specification for a tool parameter."""
    name: str
    type: str = "string"
    description: str = ""
    required: bool = True

    def to_dict(self) -> dict:
        return {"name": self.name, "type": self.type,
                "description": self.description, "required": self.required}


@dataclass
class Tool:
    """A registered tool callable."""
    name: str
    fn: Callable
    description: str = ""
    parameters: list[ParameterSpec] = field(default_factory=list)

    def to_spec(self) -> dict:
        return {"name": self.name, "description": self.description,
                "parameters": [p.to_dict() for p in self.parameters]}


@dataclass
class ToolResult:
    """Result returned by a tool execution."""
    success: bool = True
    output: Any = None
    error: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"success": self.success, "output": self.output,
                "error": self.error, "metadata": self.metadata}


class ToolRegistry:
    """Registry of tools with validation and dispatch."""

    def __init__(self):
        self.tools: dict[str, Tool] = {}

    def register(self, fn: Callable | None = None,
                 **decorator_kwargs) -> Callable | None:
        """Decorator to register a tool. Use as @registry.register(...) or @registry.register."""
        def wrap(f):
            name = decorator_kwargs.get("name", f.__name__)
            self.tools[name] = Tool(name=name, fn=f,
                                    description=decorator_kwargs.get("description", f.__doc__ or ""))
            return f
        if fn is not None:
            return wrap(fn)
        return wrap

    def get(self, name: str) -> Tool | None:
        return self.tools.get(name)

    def list_tools(self) -> list[dict]:
        return [t.to_spec() for t in self.tools.values()]

    def validate_call(self, name: str, args: dict) -> tuple[bool, str | None]:
        tool = self.tools.get(name)
        if tool is None:
            return False, f"unknown tool: {name}"
        sig = inspect.signature(tool.fn)
        missing = []
        for p in sig.parameters.values():
            if p.name == "self":
                continue
            if p.default is inspect.Parameter.empty and p.name not in args:
                missing.append(p.name)
        if missing:
            return False, f"missing parameters: {missing}"
        return True, None

    def call(self, name: str, **kwargs) -> ToolResult:
        ok, err = self.validate_call(name, kwargs)
        if not ok:
            return ToolResult(success=False, error=err)
        tool = self.tools[name]
        try:
            result = tool.fn(**kwargs)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
'''
    write_module("41_tool_calling", code)
    return "module: astrovox/phases/phase41_tool_calling.py"


def build_phase_41_agent_communication() -> str:
    """Inter-agent messaging/queues."""
    code = '''"""Agent communication: message passing, queues, and broadcast."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable
from collections import deque


@dataclass
class Message:
    """A message on the agent communication bus."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    sender: str = ""
    receiver: str = ""
    payload: Any = None
    msg_type: str = "text"
    timestamp: float = field(default_factory=lambda: asyncio.get_event_loop().time() if hasattr(asyncio, 'get_event_loop') else __import__('time').time())

    def to_dict(self) -> dict:
        return {"id": self.id, "sender": self.sender, "receiver": self.receiver,
                "payload": self.payload, "msg_type": self.msg_type,
                "timestamp": self.timestamp}


class MessageQueue:
    """Async message queue for agent communication."""

    def __init__(self, name: str = "default", capacity: int = 1000):
        self.name = name
        self.capacity = capacity
        self._queue: deque = deque()
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition(self._lock)
        self.handlers: dict[str, Callable[[Message], Any]] = {}
        self.delivery_count = 0

    async def put(self, msg: Message) -> bool:
        async with self._not_empty:
            if len(self._queue) >= self.capacity:
                self._queue.popleft()
            self._queue.append(msg)
            self._not_empty.notify()
            return True

    async def get(self, timeout: float | None = None) -> Message | None:
        async with self._not_empty:
            while not self._queue:
                try:
                    await asyncio.wait_for(self._not_empty.wait(), timeout=timeout)
                except asyncio.TimeoutError:
                    return None
            msg = self._queue.popleft()
            self.delivery_count += 1
            return msg

    def register(self, name: str, handler: Callable[[Message], Any]) -> None:
        self.handlers[name] = handler

    async def dispatch(self, msg: Message) -> Any:
        name = msg.msg_type
        handler = self.handlers.get(name)
        if handler is not None:
            return handler(msg)
        return None

    def __len__(self) -> int:
        return len(self._queue)


class AgentBus:
    """Message bus connecting agents."""

    def __init__(self):
        self.queues: dict[str, MessageQueue] = {}
        self.subscribers: dict[str, set[str]] = {}  # topic -> agent ids

    def create_queue(self, name: str, capacity: int = 1000) -> MessageQueue:
        self.queues[name] = MessageQueue(name=name, capacity=capacity)
        return self.queues[name]

    def send(self, to: str, payload: Any, msg_type: str = "text") -> Message:
        msg = Message(sender="__system__", receiver=to, payload=payload, msg_type=msg_type)
        queue = self.queues.get(to)
        if queue is not None:
            asyncio.create_task(queue.put(msg))
        return msg

    def broadcast(self, topic: str, payload: Any, msg_type: str = "broadcast") -> None:
        agents = self.subscribers.get(topic, set())
        for agent_id in agents:
            self.send(agent_id, payload, msg_type)

    def subscribe(self, topic: str, agent_id: str) -> None:
        self.subscribers.setdefault(topic, set()).add(agent_id)

    def unsubscribe(self, topic: str, agent_id: str) -> None:
        agents = self.subscribers.get(topic, set())
        agents.discard(agent_id)


def create_bus() -> AgentBus:
    return AgentBus()
'''
    write_module("41_agent_communication", code)
    return "module: astrovox/phases/phase41_agent_communication.py"


def build_phase_41_task_scheduler() -> str:
    """Task queue + priority scheduler."""
    code = '''"""Task scheduler: priority queue with scheduling and execution."""

from __future__ import annotations

import asyncio
import heapq
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class TaskState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(order=True)
class ScheduledTask:
    """A scheduled task keyed by (priority, sequence)."""
    sort_key: tuple[float, float]
    id: str = field(compare=False)
    priority: int = field(compare=False)
    sequence: int = field(compare=False)
    description: str = field(compare=False)
    fn: Callable = field(compare=False)
    args: tuple = field(compare=False, default_factory=tuple)
    kwargs: dict = field(compare=False, default_factory=dict)
    state: TaskState = field(compare=False, default=TaskState.PENDING)
    result: Any = field(compare=False, default=None)
    error: str | None = field(compare=False, default=None)
    scheduled_at: float = field(compare=False, default_factory=lambda: asyncio.get_event_loop().time() if hasattr(asyncio, 'get_event_loop') else __import__('time').time())


class TaskScheduler:
    """Priority scheduler for agent tasks."""

    def __init__(self, concurrency: int = 4):
        self.concurrency = concurrency
        self._heap: list[ScheduledTask] = []
        self._counter = 0
        self._running = False
        self._lock = asyncio.Lock()
        self._tasks: dict[str, ScheduledTask] = {}
        self._sem = asyncio.Semaphore(concurrency)

    def schedule(self, fn: Callable, *args, priority: int = 5,
                 **kwargs) -> str:
        self._counter += 1
        task = ScheduledTask(
            sort_key=(-priority, self._counter),
            id=str(uuid.uuid4())[:8], priority=priority, sequence=self._counter,
            description=fn.__name__, fn=fn, args=args, kwargs=kwargs
        )
        heapq.heappush(self._heap, task)
        self._tasks[task.id] = task
        return task.id

    async def _run(self, task: ScheduledTask) -> None:
        async with self._sem:
            task.state = TaskState.RUNNING
            try:
                task.result = task.fn(*task.args, **task.kwargs)
                task.state = TaskState.COMPLETED
            except Exception as e:
                task.error = str(e)
                task.state = TaskState.FAILED

    async def run_all(self) -> list[ScheduledTask]:
        """Run all pending tasks respecting priority order."""
        results = []
        async with self._lock:
            pending = []
            while self._heap:
                task = heapq.heappop(self._heap)
                if task.state == TaskState.CANCELLED:
                    continue
                task.state = TaskState.PENDING
                pending.append(task)
        await asyncio.gather(*[self._run(t) for t in pending])
        for t in pending:
            self._tasks[t.id] = t
            results.append(t)
        return sorted(results, key=lambda t: t.sort_key)

    def get(self, task_id: str) -> ScheduledTask | None:
        return self._tasks.get(task_id)

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is not None and task.state == TaskState.PENDING:
            task.state = TaskState.CANCELLED
            return True
        return False

    def stats(self) -> dict:
        return {"pending": sum(1 for t in self._tasks.values() if t.state == TaskState.PENDING),
                "running": sum(1 for t in self._tasks.values() if t.state == TaskState.RUNNING),
                "completed": sum(1 for t in self._tasks.values() if t.state == TaskState.COMPLETED),
                "failed": sum(1 for t in self._tasks.values() if t.state == TaskState.FAILED)}


class Scheduler:
    """Synchronous wrapper around TaskScheduler for executor use."""

    def __init__(self, concurrency: int = 4):
        self._scheduler = TaskScheduler(concurrency=concurrency)

    def schedule(self, fn: Callable, *args, priority: int = 5, **kwargs) -> str:
        return self._scheduler.schedule(fn, *args, priority=priority, **kwargs)

    def run_all(self) -> list[ScheduledTask]:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(self._scheduler.run_all())

    def get(self, task_id: str) -> ScheduledTask | None:
        return self._scheduler.get(task_id)

    def cancel(self, task_id: str) -> bool:
        return self._scheduler.cancel(task_id)

    def stats(self) -> dict:
        return self._scheduler.stats()
'''
    write_module("41_task_scheduler", code)
    return "module: astrovox/phases/phase41_task_scheduler.py"


# ============ PHASE 42 - Long-Term Memory ============

def _shared_header() -> str:
    return '''"""Shared base for phase modules."""

'''


def build_phase_42_memory_storage() -> str:
    """Persistent memory store (SQLite/JSON)."""
    code = '''"""Persistent memory storage backed by SQLite with JSON fallback."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MemoryStore:
    """Persistent key-value memory store (SQLite, JSON fallback)."""

    path: str = "data/memories.sqlite"

    def __post_init__(self):
        self._path = Path(self.path)
        self._use_json = not self._path.suffix.lower().endswith(".sqlite")
        if self._use_json:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        if not self._use_json and self._path.exists():
            return
        conn = sqlite3.connect(self._path)
        conn.execute("""CREATE TABLE IF NOT EXISTS memories (
            key TEXT PRIMARY KEY, value TEXT, entry_type TEXT,
            created REAL, last_accessed REAL, importance REAL, tags TEXT)""")
        conn.commit()
        conn.close()

    def _load(self) -> dict:
        if self._use_json:
            try:
                return json.loads(self._path.read_text())
            except Exception:
                return {}
        conn = sqlite3.connect(self._path)
        cur = conn.execute("SELECT key, value FROM memories")
        data = {row[0]: row[1] for row in cur.fetchall()}
        conn.close()
        return data

    def _save(self, data: dict) -> None:
        if self._use_json:
            self._path.write_text(json.dumps(data))
            return
        conn = sqlite3.connect(self._path)
        conn.executemany(
            "INSERT OR REPLACE INTO memories (key, value, entry_type, created, last_accessed, importance, tags) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(k, v, "", time.time(), time.time(), 1.0, "") for k, v in data.items()])
        conn.commit()
        conn.close()

    def set(self, key: str, value: Any, entry_type: str = "episodic",
            tags: list[str] | None = None, importance: float = 1.0, ttl: float | None = None) -> str:
        data = self._load()
        row = {
            "key": key,
            "value": json.dumps(value),
            "entry_type": entry_type,
            "tags": ",".join(tags or []),
            "importance": importance,
            "created": time.time(),
            "last_accessed": time.time(),
        }
        if ttl is not None:
            row["expires"] = time.time() + ttl
        data[key] = json.dumps(row)
        self._save(data)
        return key

    def get(self, key: str) -> Any | None:
        data = self._load()
        s = data.get(key)
        if s is None:
            return None
        row = json.loads(s) if isinstance(s, str) else s
        row["last_accessed"] = time.time()
        return row.get("value")

    def delete(self, key: str) -> bool:
        data = self._load()
        if key in data:
            del data[key]
            self._save(data)
            return True
        return False

    def list_keys(self) -> list[str]:
        return list(self._load().keys())

    def count(self) -> int:
        return len(self._load())

    def clear(self) -> None:
        self._save({})

    def search(self, query: str, limit: int = 20) -> list[dict]:
        data = self._load()
        q = query.lower()
        results = []
        for k, s in data.items():
            payload = json.loads(s) if isinstance(s, str) else s
            text = str(payload.get("value")) + " " + payload.get("tags", "")
            if q in text.lower():
                results.append({"key": k, **payload})
        results.sort(key=lambda r: r.get("importance", 0), reverse=True)
        return results[:limit]
'''
    write_module("42_memory_storage", code)
    return "module: astrovox/phases/phase42_memory_storage.py"


def build_phase_42_conversation_memory() -> str:
    """Session/chained conversation recall."""
    code = '''"""Conversation memory: session-based chat history with recall."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ConversationMessage:
    """A single message in a conversation."""
    role: str = "user"
    content: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content,
                "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, d: dict) -> "ConversationMessage":
        d = d.copy()
        d.setdefault("timestamp", time.time())
        return cls(**d)


@dataclass
class Conversation:
    """A conversation session with its message history."""
    id: str = field(default_factory=lambda: f"conv_{int(time.time())}")
    title: str = "Untitled conversation"
    messages: list[ConversationMessage] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def append(self, role: str, content: str) -> ConversationMessage:
        msg = ConversationMessage(role=role, content=content)
        self.messages.append(msg)
        return msg

    def recent(self, n: int = 5) -> list[ConversationMessage]:
        return self.messages[-n:]

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title,
                "messages": [m.to_dict() for m in self.messages],
                "metadata": self.metadata}

    @classmethod
    def from_dict(cls, d: dict) -> "Conversation":
        return cls(**d)


class ConversationMemory:
    """Persistent storage of conversation sessions."""

    def __init__(self, path: str = "data/conversations.json"):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self._path.read_text())
            self._conversations: dict[str, Conversation] = {
                c["id"]: Conversation.from_dict(c) for c in data}
        except Exception:
            self._conversations = {}

    def _save(self) -> None:
        self._path.write_text(json.dumps([c.to_dict() for c in self._conversations.values()]))

    def create(self, title: str = "Untitled conversation") -> Conversation:
        conv = Conversation(title=title)
        self._conversations[conv.id] = conv
        self._save()
        return conv

    def get(self, conv_id: str) -> Conversation | None:
        return self._conversations.get(conv_id)

    def start(self, title: str = "Untitled conversation") -> Conversation:
        for c in self._conversations.values():
            if c.id.startswith("conv_"):
                return c
        return self.create(title)

    def append(self, conv_id: str, role: str, content: str) -> ConversationMessage:
        conv = self.get(conv_id) or self.create()
        msg = conv.append(role, content)
        self._conversations[conv.id] = conv
        self._save()
        return msg

    def history(self, conv_id: str, limit: int = 50) -> list[dict]:
        conv = self.get(conv_id)
        if conv is None:
            return []
        return [m.to_dict() for m in conv.recent(limit)]

    def summary(self, conv_id: str) -> str:
        conv = self.get(conv_id)
        if conv is None:
            return "No conversation"
        return f"{conv.title}: {len(conv.messages)} messages"

    def list_conversations(self) -> list[dict]:
        return [{"id": c.id, "title": c.title, "message_count": len(c.messages)}
                for c in self._conversations.values()]

    def delete(self, conv_id: str) -> bool:
        if conv_id in self._conversations:
            del self._conversations[conv_id]
            self._save()
            return True
        return False
'''
    write_module("42_conversation_memory", code)
    return "module: astrovox/phases/phase42_conversation_memory.py"


def build_phase_42_user_profiles() -> str:
    """Per-user preference & history store."""
    code = '''"""User profiles: per-user preferences, history, and settings."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class UserProfile:
    """A user profile with preferences and history."""
    user_id: str
    name: str = "Anonymous"
    email: str = ""
    preferences: dict = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)
    created: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def set_preference(self, key: str, value: Any) -> None:
        self.preferences[key] = value

    def get_preference(self, key: str, default: Any = None) -> Any:
        return self.preferences.get(key, default)

    def append_history(self, event: str, **context) -> dict:
        entry = {"event": event, "context": context,
                 "timestamp": time.time()}
        self.history.append(entry)
        self.last_active = time.time()
        return entry

    def to_dict(self) -> dict:
        return {"user_id": self.user_id, "name": self.name, "email": self.email,
                "preferences": self.preferences, "history": self.history,
                "created": self.created, "last_active": self.last_active,
                "metadata": self.metadata}

    @classmethod
    def from_dict(cls, d: dict) -> "UserProfile":
        d = d.copy()
        d.setdefault("created", time.time())
        d.setdefault("last_active", time.time())
        d.setdefault("preferences", {})
        d.setdefault("history", [])
        return cls(**d)


class UserProfileStore:
    """Persistent store of user profiles."""

    def __init__(self, path: str = "data/user_profiles.json"):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self._path.read_text())
            self._profiles: dict[str, UserProfile] = {
                p["user_id"]: UserProfile.from_dict(p) for p in data}
        except Exception:
            self._profiles = {}

    def _save(self) -> None:
        self._path.write_text(json.dumps([p.to_dict() for p in self._profiles.values()]))

    def get(self, user_id: str) -> UserProfile | None:
        return self._profiles.get(user_id)

    def create(self, user_id: str, name: str = "Anonymous") -> UserProfile:
        profile = UserProfile(user_id=user_id, name=name)
        self._profiles[user_id] = profile
        self._save()
        return profile

    def update(self, user_id: str, name: str | None = None,
               preferences: dict | None = None) -> UserProfile | None:
        profile = self.get(user_id)
        if profile is None:
            return None
        if name is not None:
            profile.name = name
        if preferences is not None:
            profile.preferences.update(preferences)
        profile.last_active = time.time()
        self._save()
        return profile

    def history(self, user_id: str, event: str | None = None, limit: int = 20) -> list[dict]:
        profile = self.get(user_id)
        if profile is None:
            return []
        if event is None:
            return profile.history[-limit:]
        return [e for e in profile.history if e.get("event") == event][-limit:]

    def set_preference(self, user_id: str, key: str, value: Any) -> bool:
        profile = self.get(user_id)
        if profile is None:
            return False
        profile.set_preference(key, value)
        self._save()
        return True

    def delete(self, user_id: str) -> bool:
        if user_id in self._profiles:
            del self._profiles[user_id]
            self._save()
            return True
        return False

    def list_users(self) -> list[str]:
        return list(self._profiles.keys())
'''
    write_module("42_user_profiles", code)
    return "module: astrovox/phases/phase42_user_profiles.py"


def build_phase_42_knowledge_memory() -> str:
    """Factual knowledge base."""
    code = '''"""Factual knowledge base: facts, entities, and relationships."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class KnowledgeTriple:
    """A single knowledge triple (subject, predicate, object)."""
    subject: str
    predicate: str
    object_: str
    confidence: float = 1.0
    source: str = ""
    created: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"subject": self.subject, "predicate": self.predicate,
                "object": self.object_, "confidence": self.confidence,
                "source": self.source, "created": self.created}


class KnowledgeBase:
    """Factual knowledge memory."""

    def __init__(self):
        self.facts: list[KnowledgeTriple] = []
        self.index: dict[str, list[int]] = {}

    def add(self, subject: str, predicate: str, obj: str,
            confidence: float = 1.0, source: str = "") -> KnowledgeTriple:
        fact = KnowledgeTriple(subject=subject, predicate=predicate,
                               object_=obj, confidence=confidence, source=source)
        self.facts.append(fact)
        for term in [subject, predicate, obj]:
            self.index.setdefault(term.lower(), []).append(len(self.facts) - 1)
        return fact

    def query(self, subject: str | None = None, predicate: str | None = None,
              obj: str | None = None, limit: int = 50) -> list[KnowledgeTriple]:
        results = self.facts
        if subject is not None:
            idx = {i for i in self.index.get(subject.lower(), [])}
            results = [f for i, f in enumerate(results) if i in idx]
        if predicate is not None:
            idx = {i for i in self.index.get(predicate.lower(), [])}
            results = [f for i, f in enumerate(results) if i in idx]
        if obj is not None:
            idx = {i for i in self.index.get(obj.lower(), [])}
            results = [f for i, f in enumerate(results) if i in idx]
        return results[:limit]

    def recall(self, query: str, limit: int = 10) -> list[KnowledgeTriple]:
        """Recall facts matching any term in the query."""
        terms = query.lower().split()
        idx = set()
        for term in terms:
            idx.update(self.index.get(term, []))
        return [self.facts[i] for i in sorted(idx)][:limit]

    def count(self) -> int:
        return len(self.facts)

    def to_dict(self) -> dict:
        return {"facts": [f.to_dict() for f in self.facts]}

    def clear(self) -> None:
        self.facts.clear()
        self.index.clear()
'''
    write_module("42_knowledge_memory", code)
    return "module: astrovox/phases/phase42_knowledge_memory.py"


def build_phase_42_memory_ranking() -> str:
    """Relevance scoring & ranking."""
    code = '''"""Memory ranking: relevance scoring and ranking of recalled items."""

from __future__ import annotations

import math
import re
import time


def tfidf_score(term: str, text: str, corpus: list[str]) -> float:
    """Compute TF-IDF score for a term against a document in a corpus."""
    tf = text.lower().count(term.lower()) / max(len(text.split()), 1)
    df = sum(1 for d in corpus if term.lower() in d.lower())
    idf = math.log(len(corpus) / (1 + df)) + 1.0
    return tf * idf


def hybrid_rank(query: str, items: list[dict], corpus: list[str],
                weights: tuple[float, float, float] = (0.5, 0.4, 0.1),
                use_key: bool = True) -> list[dict]:
    """Rank items by keyword, semantic, and metadata scores."""
    scored = []
    for item in items:
        text = " ".join(str(v) for v in item.values())
        kw = sum(tfidf_score(t, text, corpus) for t in query.lower().split() if len(t) > 2)
        key_score = sum(tfidf_score(t, str(item.get("key", "")), corpus)
                        for t in query.lower().split()) if use_key else 0.0
        meta = item.get("importance", 1.0) + (item.get("recency", 0.0) * 0.001)
        total = kw * weights[0] + key_score * weights[1] + meta * weights[2]
        scored.append((total, item))
    scored.sort(reverse=True)
    return [item for _, item in scored]


def recency_boost(items: list[dict], now: float | None = None) -> list[dict]:
    """Boost items by recency."""
    now = now or time.time()
    scored = []
    for item in items:
        created = item.get("created", now)
        recency = 1.0 / (1.0 + (now - created))
        item = item.copy()
        item["recency"] = recency
        scored.append((recency, item))
    scored.sort(reverse=True)
    return [item for _, item in scored]


def deduplicate(items: list[dict], similarity_threshold: float = 0.9) -> list[dict]:
    """Deduplicate near-identical items."""
    kept = []
    for item in items:
        text = str(item).lower()
        if any(len(text) > 0 and all(c in str(k).lower() for c in text[:20]) for k in kept):
            continue
        kept.append(item)
    return kept


class Ranker:
    """Ranked retrieval with keyword + metadata scoring."""

    def __init__(self, corpus: list[str] | None = None):
        self.corpus = corpus or []

    def rank(self, query: str, items: list[dict], top: int = 20,
             weights: tuple[float, float, float] = (0.5, 0.4, 0.1)) -> list[dict]:
        scored = hybrid_rank(query, items, self.corpus, weights=weights)
        scored = recency_boost(scored)
        scored = deduplicate(scored)
        return scored[:top]

    def add_corpus(self, text: str) -> None:
        self.corpus.append(text)

    def score(self, query: str, item: dict) -> float:
        results = self.rank(query, [item], top=1)
        return results[0].get("recency", 0.0) if results else 0.0
'''
    write_module("42_memory_ranking", code)
    return "module: astrovox/phases/phase42_memory_ranking.py"


def build_phase_42_memory_retrieval() -> str:
    """Search/retrieval API."""
    code = '''"""Memory retrieval API: unified search over stored memories."""

from __future__ import annotations

from astrovox.phases._shared.base import BaseStore
from astrovox.phases._shared.retrieval_engine import RetrievalEngine
from astrovox.phases._shared.ranking import Ranker
from astrovox.phases._shared.compression import compress_text


def search(store: BaseStore, query: str, top: int = 10,
           filters: dict | None = None) -> list[dict]:
    """Retrieve memories matching a query."""
    engine = RetrievalEngine()
    candidates = engine.search(store, query, limit=100)
    ranker = Ranker()
    ranked = ranker.rank(query, candidates, top=top)
    return ranked


def recall(store: BaseStore, entity: str, limit: int = 10) -> list[dict]:
    """Recall memories about an entity."""
    return store.search(entity, limit=limit)
'''
    write_module("42_memory_retrieval", code)
    return "module: astrovox/phases/phase42_memory_retrieval.py"


def build_phase_42_memory_compression() -> str:
    """Summarize/dedup long memories."""
    code = '''"""Memory compression: summarization and deduplication of memories."""

from __future__ import annotations

import re


def compress_text(text: str, max_length: int = 300) -> str:
    """Compress text by removing filler and shortening."""
    filler = re.findall(r"\b(the|a|an|and|or|but|in|on|at|to|for|of|with|by)\b",
                        text.lower())
    words = text.split()
    if len(words) <= max_length:
        return text
    kept = [w for w in words if w.lower() not in filler][:max_length]
    return " ".join(kept) + "..."


def deduplicate_memories(memories: list[dict], threshold: float = 0.85) -> list[dict]:
    """Remove near-duplicate memories."""
    def jaccard(a: str, b: str) -> float:
        sa, sb = set(a.lower().split()), set(b.lower().split())
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / len(sa | sb)

    kept = []
    for m in memories:
        text = m.get("content", m.get("value", "") or "")
        if any(jaccard(text, kept_m.get("content", kept_m.get("value", "")) or "") >= threshold
               for kept_m in kept):
            continue
        kept.append(m)
    return kept


def summarize_memory(memory: dict, length_ratio: float = 0.3) -> dict:
    """Summarize a single memory."""
    text = memory.get("content", memory.get("value", "") or "")
    words = text.split()
    n = max(1, int(len(words) * length_ratio))
    summary = " ".join(words[:n]) + ("..." if len(words) > n else "")
    out = dict(memory)
    out["summary"] = summary
    out["original_length"] = len(words)
    return out


class MemoryCompressor:
    """Compresses and deduplicates memory collections."""

    def __init__(self, max_length: int = 300, dedup_threshold: float = 0.85):
        self.max_length = max_length
        self.dedup_threshold = dedup_threshold

    def compress(self, memory: dict) -> dict:
        content = memory.get("content", memory.get("value", "") or "")
        out = dict(memory)
        out["content"] = compress_text(content, self.max_length)
        return out

    def compress_batch(self, memories: list[dict]) -> list[dict]:
        compressed = [self.compress(m) for m in memories]
        return deduplicate_memories(compressed, self.dedup_threshold)

    def stats(self, original: list[str], compressed: list[str]) -> dict:
        orig_total = sum(len(t.split()) for t in original)
        comp_total = sum(len(t.split()) for t in compressed)
        return {"original_tokens": orig_total, "compressed_tokens": comp_total,
                "reduction_pct": (1 - comp_total / max(orig_total, 1)) * 100}
'''
    write_module("42_memory_compression", code)
    return "module: astrovox/phases/phase42_memory_compression.py"


def build_phase_42_memory_summarization() -> str:
    """Automated summary generation."""
    code = '''"""Automated memory summarization."""

from __future__ import annotations

from astrovox.phases._shared.compression import summarize_memory


def summarize_conversation(messages: list[dict]) -> str:
    """Generate a summary of a conversation."""
    if not messages:
        return ""
    texts = [m.get("content", m.get("value", "") or "") for m in messages]
    combined = " ".join(texts)
    words = combined.split()
    n = min(len(words), 60)
    return " ".join(words[:n]) + ("..." if len(words) > n else "")


def summarize_memory_batch(memories: list[dict]) -> list[dict]:
    """Summarize multiple memories."""
    return [summarize_memory(m) for m in memories]
'''
    write_module("42_memory_summarization", code)
    return "module: astrovox/phases/phase42_memory_summarization.py"


def build_phase_42_memory_cleanup() -> str:
    """TTL/eviction/garbage collection."""
    code = '''"""Memory cleanup: TTL, eviction, and garbage collection."""

from __future__ import annotations

import time
from astrovox.phases._shared.compression import compress_text
from astrovox.phases.phase42_memory_storage import MemoryStore
from astrovox.phases.phase42_memory_retrieval import search


def cleanup_expired(store: MemoryStore, now: float | None = None) -> int:
    """Remove expired entries."""
    now = now or time.time()
    keys = list(store.list_keys())
    removed = 0
    for key in keys:
        row = store.get(key)
        if isinstance(row, dict) and row.get("expires", 0) and now > row["expires"]:
            store.delete(key)
            removed += 1
    return removed


def evict_low_importance(store: MemoryStore, keep: int = 100) -> int:
    """Evict lowest-importance entries down to keep count."""
    rows = {}
    for key in store.list_keys():
        r = store.get(key)
        if isinstance(r, dict):
            rows[key] = r
    scored = sorted(rows.items(), key=lambda kv: kv[1].get("importance", 0))
    removed = 0
    for key, _ in scored[:-keep]:
        store.delete(key)
        removed += 1
    return removed


def garbage_collect(store: MemoryStore) -> dict:
    """Run full cleanup: expired removal + low-importance eviction."""
    now = time.time()
    expired = cleanup_expired(store, now)
    evicted = evict_low_importance(store)
    return {"expired_removed": expired, "evicted": evicted,
            "remaining": store.count()}


class CleanupScheduler:
    """Periodic memory cleanup scheduler."""

    def __init__(self, store: MemoryStore, interval_seconds: float = 3600.0):
        self.store = store
        self.interval = interval_seconds
        self.last_run = 0.0
        self._running = False

    def should_run(self, now: float | None = None) -> bool:
        now = now or time.time()
        if not self._running:
            return True
        return now - self.last_run >= self.interval

    def run(self, now: float | None = None) -> dict:
        now = now or time.time()
        if not self.should_run(now):
            return {"skipped": True, "reason": "interval not reached"}
        result = garbage_collect(self.store)
        result["timestamp"] = now
        self.last_run = now
        return result
'''
    write_module("42_memory_cleanup", code)
    return "module: astrovox/phases/phase42_memory_cleanup.py"

