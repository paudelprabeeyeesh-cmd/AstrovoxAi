"""Tests for workflow automation engine."""

import pytest
from app.workflow_engine import (
    WorkflowEngine,
    Workflow,
    WorkflowStep,
    WorkflowExecution,
    WorkflowStatus,
    StepAction,
)


class TestWorkflowEngine:
    def test_create_workflow(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow("Test", "Description")
        assert wf.id is not None
        assert wf.name == "Test"

    def test_add_step(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow("Test")
        step = engine.add_step(wf.id, "Step1", StepAction.AGENT_TASK)
        assert step is not None
        assert len(wf.steps) == 1

    def test_create_template(self):
        engine = WorkflowEngine()
        template = engine.create_template("Template", "A template")
        assert template.is_template is True

    def test_clone_workflow(self):
        engine = WorkflowEngine()
        template = engine.create_template("Template")
        engine.add_step(template.id, "Step1", StepAction.AGENT_TASK)
        clone = engine.clone_workflow(template.id, "Clone")
        assert clone is not None
        assert clone.name == "Clone"
        assert len(clone.steps) == 1

    def test_clone_non_template_fails(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow("Not template")
        clone = engine.clone_workflow(wf.id, "Clone")
        assert clone is None

    @pytest.mark.asyncio
    async def test_execute_workflow(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow("Test")
        engine.add_step(wf.id, "Step1", StepAction.AGENT_TASK)
        result = await engine.execute_workflow(wf.id)
        assert result.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_workflow_with_dependencies(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow("Test")
        s1 = engine.add_step(wf.id, "Step1", StepAction.AGENT_TASK)
        s2 = engine.add_step(wf.id, "Step2", StepAction.AGENT_TASK, dependencies=[s1.id])
        result = await engine.execute_workflow(wf.id)
        assert result.status == WorkflowStatus.COMPLETED

    def test_cancel_execution(self):
        engine = WorkflowEngine()
        assert engine.cancel_execution("nonexistent") is False

    def test_get_workflow(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow("Test")
        assert engine.get_workflow(wf.id) is wf

    def test_list_workflows(self):
        engine = WorkflowEngine()
        engine.create_workflow("W1")
        engine.create_workflow("W2")
        assert len(engine.list_workflows()) == 2

    def test_list_templates(self):
        engine = WorkflowEngine()
        engine.create_template("T1")
        engine.create_workflow("W1")
        assert len(engine.list_templates()) == 1

    def test_get_analytics(self):
        engine = WorkflowEngine()
        engine.create_workflow("Test")
        analytics = engine.get_analytics()
        assert analytics["total_workflows"] == 1


class TestWorkflowStep:
    def test_step_creation(self):
        step = WorkflowStep(id="s1", name="Test", action=StepAction.AGENT_TASK)
        assert step.status == "pending"

    def test_step_with_dependencies(self):
        step = WorkflowStep(id="s1", name="Test", action=StepAction.AGENT_TASK, dependencies=["s0"])
        assert len(step.dependencies) == 1


class TestWorkflowExecution:
    def test_execution_creation(self):
        exec = WorkflowExecution(id="e1", workflow_id="w1")
        assert exec.status == WorkflowStatus.PENDING
