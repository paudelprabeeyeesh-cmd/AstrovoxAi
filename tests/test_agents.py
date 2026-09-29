from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.agents.browser import WebBrowser
from models.llm.agents.code import CodeExecutor
from models.llm.agents.file import DirectoryTraversal, FileReader, FileSearch, FileWriter
from models.llm.agents.memory import AgentMemory, FileStorage, InMemoryStorage, MemoryEntry
from models.llm.agents.multi import Agent, AgentConfig, AgentTeam, Message
from models.llm.agents.planner import Plan, SequentialPlanner, Task
from models.llm.agents.reflection import ReflectionEngine, ReflectionResult, SelfCritiqueAgent
from models.llm.agents.tools import ParameterSpec, Tool, ToolRegistry, ToolResult


class TestToolResult:
    def test_to_dict(self):
        result = ToolResult(success=True, output={"key": "value"}, error=None, metadata={"count": 1})
        data = result.to_dict()
        assert data["success"] is True
        assert data["output"]["key"] == "value"
        assert data["error"] is None
        assert data["metadata"]["count"] == 1

    def test_defaults(self):
        result = ToolResult(success=False, output=None)
        assert result.error is None
        assert result.metadata == {}


class TestParameterSpec:
    def test_validate_string(self):
        spec = ParameterSpec(name="text", type="string", description="desc")
        assert spec.validate("hello") is True
        assert spec.validate(123) is False

    def test_validate_integer(self):
        spec = ParameterSpec(name="count", type="integer", description="desc")
        assert spec.validate(5) is True
        assert spec.validate(5.5) is False
        assert spec.validate(True) is False

    def test_validate_boolean(self):
        spec = ParameterSpec(name="flag", type="boolean", description="desc")
        assert spec.validate(True) is True
        assert spec.validate(False) is True
        assert spec.validate(0) is False

    def test_validate_enum(self):
        spec = ParameterSpec(name="mode", type="string", description="desc", enum=["a", "b"])
        assert spec.validate("a") is True
        assert spec.validate("c") is False


class TestTool:
    def test_validate_input_missing_required(self):
        class DummyTool2(Tool):
            name = "dummy2"
            description = "dummy tool"
            parameters = [ParameterSpec(name="required_param", type="string", description="desc", required=True)]

            def execute(self, **kwargs):
                return ToolResult(success=True, output="ok")

        tool = DummyTool2()
        result = tool()
        assert result.success is False
        assert "required_param" in result.error

    def test_execute_wraps_non_toolresult(self):
        class DummyTool3(Tool):
            name = "dummy3"
            description = "dummy tool"
            parameters = []

            def execute(self, **kwargs):
                return "raw output"

        tool = DummyTool3()
        result = tool()
        assert result.success is True
        assert result.output == "raw output"

    def test_to_schema(self):
        class DummyTool4(Tool):
            name = "dummy4"
            description = "dummy tool"
            parameters = [ParameterSpec(name="x", type="integer", description="desc", required=True)]

            def execute(self, **kwargs):
                return ToolResult(success=True, output="ok")

        tool = DummyTool4()
        schema = tool.to_schema()
        assert schema["name"] == "dummy4"
        assert schema["parameters"]["required"] == ["x"]


class DummyTool(Tool):
    name = "dummy"
    description = "dummy tool"
    parameters = []

    def execute(self, **kwargs: Any):
        return ToolResult(success=True, output="ok")


class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        tool = DummyTool()
        registry.register(tool)
        assert registry.get("dummy") is tool

    def test_unregister(self):
        registry = ToolRegistry()
        tool = DummyTool()
        registry.register(tool)
        registry.unregister("dummy")
        assert registry.get("dummy") is None

    def test_list_tools(self):
        registry = ToolRegistry()
        t1 = DummyTool()
        t1.name = "dummy1"
        t2 = DummyTool()
        t2.name = "dummy2"
        registry.register(t1)
        registry.register(t2)
        assert len(registry.list_tools()) == 2

    def test_execute(self):
        registry = ToolRegistry()
        tool = DummyTool()
        registry.register(tool)
        result = registry.execute("dummy")
        assert result.success is True

    def test_execute_missing(self):
        registry = ToolRegistry()
        result = registry.execute("missing")
        assert result.success is False
        assert "not found" in result.error


class TestWebBrowser:
    def setup_method(self):
        self.browser = WebBrowser()

    def test_navigate_valid(self):
        result = self.browser(action="navigate", url="https://example.com")
        assert result.success is True
        assert result.output["url"] == "https://example.com"

    def test_navigate_invalid(self):
        result = self.browser(action="navigate", url="invalid")
        assert result.success is False

    def test_extract_text(self):
        result = self.browser(action="extract", url="https://example.com")
        assert result.success is True
        assert "content" in result.output

    def test_click(self):
        result = self.browser(action="click", url="https://example.com", selector="#btn")
        assert result.success is True

    def test_fill(self):
        result = self.browser(action="fill", url="https://example.com", selector="#input", text="test")
        assert result.success is True

    def test_screenshot(self):
        result = self.browser(action="screenshot", url="https://example.com")
        assert result.success is True

    def test_unknown_action(self):
        result = self.browser(action="unknown")
        assert result.success is False


class TestCodeExecutor:
    def setup_method(self):
        self.executor = CodeExecutor()

    def test_execute_simple(self):
        result = self.executor(code="x = 1 + 1")
        assert result.success is True

    def test_execute_print(self):
        result = self.executor(code="print('hello')")
        assert result.success is True
        assert "hello" in result.output["stdout"]

    def test_execute_syntax_error(self):
        result = self.executor(code="x = ")
        assert result.success is False
        assert "SyntaxError" in result.error or "unsafe" in result.error.lower()

    def test_execute_empty(self):
        result = self.executor(code="")
        assert result.success is False

    def test_unsafe_import_blocked(self):
        result = self.executor(code="import os")
        assert result.success is False
        assert "unsafe" in result.error.lower()

    def test_eval_blocked(self):
        result = self.executor(code="eval('1+1')")
        assert result.success is False


class TestFileTools:
    def setup_method(self):
        self.tmpdir = os.path.join(ROOT, "tests", "tmp_agents")
        os.makedirs(self.tmpdir, exist_ok=True)
        self.reader = FileReader(allowed_dirs=[self.tmpdir])
        self.writer = FileWriter(allowed_dirs=[self.tmpdir])
        self.traversal = DirectoryTraversal(allowed_dirs=[self.tmpdir])
        self.search = FileSearch(allowed_dirs=[self.tmpdir])

    def teardown_method(self):
        for f in os.listdir(self.tmpdir):
            os.remove(os.path.join(self.tmpdir, f))
        os.rmdir(self.tmpdir)

    def test_file_write_and_read(self):
        write_result = self.writer(path=os.path.join(self.tmpdir, "test.txt"), content="hello world")
        assert write_result.success is True
        read_result = self.reader(path=os.path.join(self.tmpdir, "test.txt"))
        assert read_result.success is True
        assert "hello world" in read_result.output["content"]

    def test_file_read_missing(self):
        result = self.reader(path=os.path.join(self.tmpdir, "missing.txt"))
        assert result.success is False

    def test_directory_traversal(self):
        open(os.path.join(self.tmpdir, "a.txt"), "w").close()
        result = self.traversal(path=self.tmpdir)
        assert result.success is True
        names = [e["name"] for e in result.output["entries"]]
        assert "a.txt" in names

    def test_file_search(self):
        open(os.path.join(self.tmpdir, "data.txt"), "w").close()
        result = self.search(pattern=".txt", path=self.tmpdir)
        assert result.success is True
        assert any("data.txt" in m for m in result.output["matches"])


class TestPlanner:
    def setup_method(self):
        self.planner = SequentialPlanner()

        class DummyTool(Tool):
            def execute(self, **kwargs):
                return ToolResult(success=True, output="done")

        self.dummy_tool = DummyTool()
        self.dummy_tool.parameters = []
        self.dummy_tool.name = "dummy"
        self.tools = {"dummy": self.dummy_tool}

    def test_decompose(self):
        plan = self.planner.decompose("Do task one. Do task two.")
        assert len(plan.tasks) == 2
        assert plan.tasks[0].description == "Do task one"

    def test_execute(self):
        plan = self.planner.decompose("Run code")
        executed = self.planner.execute(plan, self.tools)
        assert executed.status in ("completed", "failed")

    def test_replan(self):
        plan = self.planner.decompose("Run code")
        plan.tasks[0].status = "failed"
        plan.tasks[0].error = "tool error"
        new_plan = self.planner.replan(plan, {"failure": "tool error"}, self.tools)
        assert len(new_plan.tasks) >= 1


class TestMemory:
    def setup_method(self):
        self.memory = AgentMemory(storage=InMemoryStorage())

    def test_store_and_recall(self):
        entry = self.memory.store("hello world", metadata={"tag": "greeting"})
        recalled = self.memory.recall(entry.id)
        assert recalled is not None
        assert recalled.content == "hello world"
        assert recalled.metadata["tag"] == "greeting"

    def test_forget(self):
        entry = self.memory.store("temp")
        self.memory.forget(entry.id)
        assert self.memory.recall(entry.id) is None

    def test_search(self):
        self.memory.store("python code example", metadata={"type": "code"})
        self.memory.store("lunch recipe", metadata={"type": "food"})
        results = self.memory.search("python")
        assert len(results) >= 1
        assert any("python" in str(r.content).lower() for r in results)

    def test_list_all(self):
        self.memory.store("one")
        self.memory.store("two")
        entries = self.memory.list_all()
        assert len(entries) == 2


class TestFileStorage:
    def setup_method(self):
        self.tmpdir = os.path.join(ROOT, "tests", "tmp_memory")
        os.makedirs(self.tmpdir, exist_ok=True)
        self.storage = FileStorage(self.tmpdir)

    def teardown_method(self):
        for f in os.listdir(self.tmpdir):
            os.remove(os.path.join(self.tmpdir, f))
        os.rmdir(self.tmpdir)

    def test_save_and_load(self):
        entry = MemoryEntry(id="m1", content="data", metadata={})
        self.storage.save(entry)
        loaded = self.storage.load("m1")
        assert loaded is not None
        assert loaded.content == "data"

    def test_delete(self):
        entry = MemoryEntry(id="m2", content="data", metadata={})
        self.storage.save(entry)
        self.storage.delete("m2")
        assert self.storage.load("m2") is None

    def test_list_entries(self):
        for i in range(3):
            self.storage.save(MemoryEntry(id=f"m{i}", content=f"data{i}", metadata={}))
        entries = self.storage.list_entries()
        assert len(entries) == 3


class TestReflection:
    def setup_method(self):
        self.engine = ReflectionEngine()

    def test_reflect_complete(self):
        result = self.engine.reflect("This is a complete output.")
        assert isinstance(result, ReflectionResult)
        assert result.confidence > 0

    def test_reflect_empty(self):
        result = self.engine.reflect("")
        assert isinstance(result, ReflectionResult)
        assert len(result.improvements) > 0

    def test_self_critique_agent(self):
        agent = SelfCritiqueAgent()
        result = agent.review("short")
        assert isinstance(result, ReflectionResult)


class TestMultiAgent:
    def setup_method(self):
        self.team = AgentTeam()
        config = AgentConfig(name="agent1", role="worker", capabilities=["process"], tools={})
        self.agent = Agent(config)
        self.team.add_agent(self.agent)

    def test_add_and_get_agent(self):
        assert self.team.get_agent("agent1") is self.agent

    def test_send_message(self):
        msg = self.team.send("agent1", "agent1", "hello")
        assert msg is not None
        assert msg.content == "hello"
        assert len(self.agent.inbox) == 1

    def test_broadcast(self):
        config2 = AgentConfig(name="agent2", role="worker", capabilities=["process"], tools={})
        agent2 = Agent(config2)
        self.team.add_agent(agent2)
        messages = self.team.broadcast("agent1", "all")
        assert len(messages) == 1
        assert agent2.inbox[0].content == "all"

    def test_run_round(self):
        self.team.register_handler("message", lambda msg, team: msg.content)
        msg = self.team.send("agent1", "agent1", "hello")
        results = self.team.run_round()
        assert len(results) == 1

    def test_message_log(self):
        self.team.send("agent1", "agent1", "hello")
        log = self.team.get_message_log()
        assert len(log) == 1
        assert log[0]["content"] == "hello"
