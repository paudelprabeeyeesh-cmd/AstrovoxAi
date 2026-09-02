"""Tests for specialized AI agents."""

import pytest
from app.specialized_agents import (
    ResearchAgent,
    CodingAgent,
    DocumentationAgent,
    MemoryAgent,
    PlanningAgent,
    FileAnalysisAgent,
    SecurityAgent,
    TestingAgent,
    DebuggingAgent,
    ReportGenerationAgent,
    SpecializedAgentCollection,
    DocumentAnalysis,
    SecurityScanResult,
    CodeAnalysisResult,
)


class TestResearchAgent:
    @pytest.mark.asyncio
    async def test_research(self):
        agent = ResearchAgent()
        result = await agent.research("AI safety", depth=3)
        assert result["topic"] == "AI safety"
        assert len(result["sources"]) == 3

    @pytest.mark.asyncio
    async def test_verify_fact(self):
        agent = ResearchAgent()
        result = await agent.verify_fact("Earth is round")
        assert result["verified"] is True
        assert result["confidence"] > 0


class TestCodingAgent:
    @pytest.mark.asyncio
    async def test_generate_code(self):
        agent = CodingAgent()
        code = await agent.generate_code("sort a list", "python")
        assert "def solution()" in code

    @pytest.mark.asyncio
    async def test_review_code(self):
        agent = CodingAgent()
        result = await agent.review_code("def foo(): pass")
        assert isinstance(result, CodeAnalysisResult)
        assert result.language == "python"

    @pytest.mark.asyncio
    async def test_debug_code(self):
        agent = CodingAgent()
        result = await agent.debug_code("def foo()", "SyntaxError")
        assert "fix" in result

    @pytest.mark.asyncio
    async def test_refactor_code(self):
        agent = CodingAgent()
        result = await agent.refactor_code("x = 1", "readability")
        assert "Refactored" in result


class TestDocumentationAgent:
    @pytest.mark.asyncio
    async def test_generate_docs(self):
        agent = DocumentationAgent()
        docs = await agent.generate_docs("def foo(): pass")
        assert '"""' in docs

    @pytest.mark.asyncio
    async def test_generate_api_docs(self):
        agent = DocumentationAgent()
        endpoints = [{"method": "GET", "path": "/users"}]
        docs = await agent.generate_api_docs(endpoints)
        assert "GET" in docs

    @pytest.mark.asyncio
    async def test_generate_readme(self):
        agent = DocumentationAgent()
        readme = await agent.generate_readme("MyProject", "A project")
        assert "# MyProject" in readme

    @pytest.mark.asyncio
    async def test_generate_changelog(self):
        agent = DocumentationAgent()
        changes = [{"type": "added", "description": "New feature"}]
        changelog = await agent.generate_changelog(changes)
        assert "# Changelog" in changelog


class TestMemoryAgent:
    @pytest.mark.asyncio
    async def test_store_memory(self):
        agent = MemoryAgent()
        result = await agent.store_memory("Test memory", 2)
        assert result["stored"] is True

    @pytest.mark.asyncio
    async def test_retrieve_memories(self):
        agent = MemoryAgent()
        results = await agent.retrieve_memories("test", 5)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_consolidate_memories(self):
        agent = MemoryAgent()
        result = await agent.consolidate_memories([{"content": "m1"}, {"content": "m2"}])
        assert result["consolidated"] is True


class TestPlanningAgent:
    @pytest.mark.asyncio
    async def test_create_plan(self):
        agent = PlanningAgent()
        plan = await agent.create_plan("Build app")
        assert len(plan["steps"]) > 0

    @pytest.mark.asyncio
    async def test_analyze_dependencies(self):
        agent = PlanningAgent()
        result = await agent.analyze_dependencies(["a", "b", "c"])
        assert len(result["tasks"]) == 3


class TestFileAnalysisAgent:
    @pytest.mark.asyncio
    async def test_analyze_document(self):
        agent = FileAnalysisAgent()
        result = await agent.analyze_document("Hello world " * 100, "text")
        assert isinstance(result, DocumentAnalysis)
        assert result.word_count > 0

    @pytest.mark.asyncio
    async def test_extract_metadata(self):
        agent = FileAnalysisAgent()
        result = await agent.extract_metadata("test.txt", b"content")
        assert result["filename"] == "test.txt"


class TestSecurityAgent:
    @pytest.mark.asyncio
    async def test_scan_code_security_clean(self):
        agent = SecurityAgent()
        result = await agent.scan_code_security("def foo(): return 1")
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_scan_code_security_dangerous(self):
        agent = SecurityAgent()
        result = await agent.scan_code_security("eval(user_input)")
        assert result.passed is False
        assert len(result.findings) > 0

    @pytest.mark.asyncio
    async def test_audit_config(self):
        agent = SecurityAgent()
        result = await agent.audit_config({"debug": True})
        assert result["passed"] is False


class TestTestingAgent:
    @pytest.mark.asyncio
    async def test_generate_tests(self):
        agent = TestingAgent()
        tests = await agent.generate_tests("def foo(): pass")
        assert "def test_" in tests

    @pytest.mark.asyncio
    async def test_analyze_coverage(self):
        agent = TestingAgent()
        result = await agent.analyze_coverage("def foo(): pass", "def test_foo(): pass")
        assert "coverage_percent" in result


class TestDebuggingAgent:
    @pytest.mark.asyncio
    async def test_analyze_error(self):
        agent = DebuggingAgent()
        result = await agent.analyze_error("SyntaxError")
        assert "suggested_fix" in result

    @pytest.mark.asyncio
    async def test_analyze_logs(self):
        agent = DebuggingAgent()
        result = await agent.analyze_logs("ERROR: something failed\nINFO: done")
        assert result["error_count"] == 1


class TestReportGenerationAgent:
    @pytest.mark.asyncio
    async def test_generate_report(self):
        agent = ReportGenerationAgent()
        report = await agent.generate_report({"title": "Test"})
        assert "# Report" in report

    @pytest.mark.asyncio
    async def test_summarize(self):
        agent = ReportGenerationAgent()
        result = await agent.summarize("Short text", 100)
        assert len(result) <= 103


class TestSpecializedAgentCollection:
    def test_list_agents(self):
        collection = SpecializedAgentCollection()
        agents = collection.list_agents()
        assert len(agents) == 10

    def test_get_agent(self):
        collection = SpecializedAgentCollection()
        agent = collection.get_agent("research")
        assert agent is not None
        assert agent.name == "ResearchAgent"

    def test_get_agent_not_found(self):
        collection = SpecializedAgentCollection()
        agent = collection.get_agent("nonexistent")
        assert agent is None
