"""
Planning Engine - Phase 2.8

For complex requests, the AI should generate an execution plan before responding.
This enables:
- Breaking down complex tasks into steps
- Showing the plan to users for approval
- Executing multi-step operations
- Tracking progress through complex workflows
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime
import json


class PlanStep:
    """Represents a single step in a plan"""
    
    def __init__(
        self,
        step_id: int,
        description: str,
        step_type: str,
        tool: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        depends_on: Optional[List[int]] = None,
        estimated_duration: Optional[int] = None,
    ):
        self.step_id = step_id
        self.description = description
        self.step_type = step_type  # "analysis", "tool_execution", "generation", "validation"
        self.tool = tool
        self.parameters = parameters or {}
        self.depends_on = depends_on or []
        self.estimated_duration = estimated_duration  # in seconds
        self.status = "pending"  # pending, in_progress, completed, failed
        self.result = None
        self.error = None
        self.started_at = None
        self.completed_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary"""
        return {
            "step_id": self.step_id,
            "description": self.description,
            "step_type": self.step_type,
            "tool": self.tool,
            "parameters": self.parameters,
            "depends_on": self.depends_on,
            "estimated_duration": self.estimated_duration,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }
    
    def start(self):
        """Mark step as started"""
        self.status = "in_progress"
        self.started_at = datetime.utcnow().isoformat()
    
    def complete(self, result: Any = None):
        """Mark step as completed"""
        self.status = "completed"
        self.result = result
        self.completed_at = datetime.utcnow().isoformat()
    
    def fail(self, error: str):
        """Mark step as failed"""
        self.status = "failed"
        self.error = error
        self.completed_at = datetime.utcnow().isoformat()


class ExecutionPlan:
    """Represents a complete execution plan"""
    
    def __init__(
        self,
        plan_id: str,
        goal: str,
        steps: List[PlanStep],
        show_to_user: bool = True,
        requires_approval: bool = False,
    ):
        self.plan_id = plan_id
        self.goal = goal
        self.steps = steps
        self.show_to_user = show_to_user
        self.requires_approval = requires_approval
        self.status = "pending"  # pending, approved, rejected, in_progress, completed, failed
        self.created_at = datetime.utcnow().isoformat()
        self.approved_at = None
        self.started_at = None
        self.completed_at = None
        self.total_estimated_duration = sum(
            s.estimated_duration or 0 for s in steps
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary"""
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "steps": [step.to_dict() for step in self.steps],
            "show_to_user": self.show_to_user,
            "requires_approval": self.requires_approval,
            "status": self.status,
            "created_at": self.created_at,
            "approved_at": self.approved_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_estimated_duration": self.total_estimated_duration,
        }
    
    def approve(self):
        """Approve the plan for execution"""
        self.status = "approved"
        self.approved_at = datetime.utcnow().isoformat()
    
    def reject(self):
        """Reject the plan"""
        self.status = "rejected"
    
    def start(self):
        """Start executing the plan"""
        self.status = "in_progress"
        self.started_at = datetime.utcnow().isoformat()
    
    def complete(self):
        """Mark plan as completed"""
        self.status = "completed"
        self.completed_at = datetime.utcnow().isoformat()
    
    def fail(self):
        """Mark plan as failed"""
        self.status = "failed"
        self.completed_at = datetime.utcnow().isoformat()
    
    def get_next_step(self) -> Optional[PlanStep]:
        """Get the next pending step that can be executed"""
        for step in self.steps:
            if step.status == "pending":
                # Check if dependencies are satisfied
                dependencies_satisfied = all(
                    self.steps[dep_id - 1].status == "completed"
                    for dep_id in step.depends_on
                )
                if dependencies_satisfied:
                    return step
        return None
    
    def get_progress(self) -> Dict[str, Any]:
        """Get progress information"""
        total = len(self.steps)
        completed = sum(1 for s in self.steps if s.status == "completed")
        failed = sum(1 for s in self.steps if s.status == "failed")
        in_progress = sum(1 for s in self.steps if s.status == "in_progress")
        
        return {
            "total_steps": total,
            "completed_steps": completed,
            "failed_steps": failed,
            "in_progress_steps": in_progress,
            "progress_percentage": (completed / total * 100) if total > 0 else 0,
        }


class PlanningEngine:
    """
    Generates and manages execution plans for complex tasks.
    """
    
    def __init__(self):
        self.plans: Dict[str, ExecutionPlan] = {}
        self.plan_templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize common plan templates"""
        return {
            "document_analysis": {
                "steps": [
                    {"description": "Read and parse document", "step_type": "analysis"},
                    {"description": "Extract key information", "step_type": "analysis"},
                    {"description": "Summarize findings", "step_type": "generation"},
                ],
            },
            "code_generation": {
                "steps": [
                    {"description": "Analyze requirements", "step_type": "analysis"},
                    {"description": "Design solution architecture", "step_type": "analysis"},
                    {"description": "Generate code", "step_type": "generation"},
                    {"description": "Review and validate code", "step_type": "validation"},
                ],
            },
            "research_task": {
                "steps": [
                    {"description": "Formulate search queries", "step_type": "analysis"},
                    {"description": "Search for information", "step_type": "tool_execution", "tool": "web_search"},
                    {"description": "Analyze findings", "step_type": "analysis"},
                    {"description": "Synthesize results", "step_type": "generation"},
                ],
            },
            "data_analysis": {
                "steps": [
                    {"description": "Load and inspect data", "step_type": "analysis"},
                    {"description": "Clean and preprocess data", "step_type": "tool_execution", "tool": "code_executor"},
                    {"description": "Perform analysis", "step_type": "tool_execution", "tool": "code_executor"},
                    {"description": "Generate visualizations", "step_type": "generation"},
                    {"description": "Create report", "step_type": "generation"},
                ],
            },
        }
    
    def generate_plan(
        self,
        goal: str,
        task_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        show_to_user: bool = True,
        requires_approval: bool = False,
    ) -> ExecutionPlan:
        """
        Generate an execution plan for a given goal.
        
        Args:
            goal: The goal to achieve
            task_type: Optional task type for template selection
            context: Additional context for plan generation
            show_to_user: Whether to show the plan to the user
            requires_approval: Whether the plan requires user approval
        
        Returns:
            ExecutionPlan
        """
        plan_id = f"plan_{datetime.utcnow().timestamp()}"
        
        # Use template if task type is provided
        if task_type and task_type in self.plan_templates:
            template = self.plan_templates[task_type]
            steps = []
            for i, step_def in enumerate(template["steps"]):
                step = PlanStep(
                    step_id=i + 1,
                    description=step_def["description"],
                    step_type=step_def["step_type"],
                    tool=step_def.get("tool"),
                    estimated_duration=self._estimate_duration(step_def["step_type"]),
                )
                steps.append(step)
        else:
            # Generate a generic plan
            steps = self._generate_generic_plan(goal, context)
        
        plan = ExecutionPlan(
            plan_id=plan_id,
            goal=goal,
            steps=steps,
            show_to_user=show_to_user,
            requires_approval=requires_approval,
        )
        
        self.plans[plan_id] = plan
        return plan
    
    def _generate_generic_plan(
        self, goal: str, context: Optional[Dict[str, Any]] = None
    ) -> List[PlanStep]:
        """Generate a generic plan based on the goal"""
        # This is a simple heuristic-based plan generator
        # In production, this could use the LLM to generate plans
        
        goal_lower = goal.lower()
        steps = []
        
        # Analyze the goal
        steps.append(
            PlanStep(
                step_id=1,
                description="Analyze requirements and understand the goal",
                step_type="analysis",
                estimated_duration=10,
            )
        )
        
        # Add task-specific steps
        if any(keyword in goal_lower for keyword in ["code", "function", "implement", "build"]):
            steps.append(
                PlanStep(
                    step_id=2,
                    description="Design solution approach",
                    step_type="analysis",
                    depends_on=[1],
                    estimated_duration=30,
                )
            )
            steps.append(
                PlanStep(
                    step_id=3,
                    description="Generate code implementation",
                    step_type="generation",
                    depends_on=[2],
                    estimated_duration=60,
                )
            )
            steps.append(
                PlanStep(
                    step_id=4,
                    description="Review and validate implementation",
                    step_type="validation",
                    depends_on=[3],
                    estimated_duration=20,
                )
            )
        
        elif any(keyword in goal_lower for keyword in ["research", "find", "look up", "investigate"]):
            steps.append(
                PlanStep(
                    step_id=2,
                    description="Search for relevant information",
                    step_type="tool_execution",
                    tool="web_search",
                    depends_on=[1],
                    estimated_duration=15,
                )
            )
            steps.append(
                PlanStep(
                    step_id=3,
                    description="Analyze and synthesize findings",
                    step_type="analysis",
                    depends_on=[2],
                    estimated_duration=30,
                )
            )
        
        elif any(keyword in goal_lower for keyword in ["analyze", "process", "calculate"]):
            steps.append(
                PlanStep(
                    step_id=2,
                    description="Perform analysis or calculations",
                    step_type="tool_execution",
                    tool="code_executor",
                    depends_on=[1],
                    estimated_duration=45,
                )
            )
            steps.append(
                PlanStep(
                    step_id=3,
                    description="Interpret results",
                    step_type="analysis",
                    depends_on=[2],
                    estimated_duration=20,
                )
            )
        
        else:
            # Generic plan
            steps.append(
                PlanStep(
                    step_id=2,
                    description="Process the request",
                    step_type="analysis",
                    depends_on=[1],
                    estimated_duration=30,
                )
            )
            steps.append(
                PlanStep(
                    step_id=3,
                    description="Generate response",
                    step_type="generation",
                    depends_on=[2],
                    estimated_duration=20,
                )
            )
        
        return steps
    
    def _estimate_duration(self, step_type: str) -> int:
        """Estimate duration for a step type in seconds"""
        durations = {
            "analysis": 30,
            "tool_execution": 45,
            "generation": 30,
            "validation": 20,
        }
        return durations.get(step_type, 30)
    
    def get_plan(self, plan_id: str) -> Optional[ExecutionPlan]:
        """Get a plan by ID"""
        return self.plans.get(plan_id)
    
    def approve_plan(self, plan_id: str) -> bool:
        """Approve a plan for execution"""
        plan = self.get_plan(plan_id)
        if plan and plan.status == "pending":
            plan.approve()
            return True
        return False
    
    def reject_plan(self, plan_id: str) -> bool:
        """Reject a plan"""
        plan = self.get_plan(plan_id)
        if plan and plan.status == "pending":
            plan.reject()
            return True
        return False
    
    async def execute_plan(
        self,
        plan_id: str,
        tool_executor: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Execute a plan step by step.
        
        Args:
            plan_id: Plan ID to execute
            tool_executor: Function to execute tools
        
        Returns:
            Execution results
        """
        plan = self.get_plan(plan_id)
        if not plan:
            return {"success": False, "error": "Plan not found"}
        
        if plan.status != "approved" and plan.requires_approval:
            return {"success": False, "error": "Plan requires approval"}
        
        plan.start()
        
        try:
            while True:
                step = plan.get_next_step()
                if not step:
                    break
                
                step.start()
                
                # Execute the step
                if step.step_type == "tool_execution" and step.tool and tool_executor:
                    result = await tool_executor(step.tool, step.parameters)
                    if result.get("success"):
                        step.complete(result)
                    else:
                        step.fail(result.get("error", "Unknown error"))
                else:
                    # For non-tool steps, mark as completed
                    # In production, these would be handled by the reasoning pipeline
                    step.complete()
                
                # Check if step failed
                if step.status == "failed":
                    plan.fail()
                    return {
                        "success": False,
                        "error": f"Step {step.step_id} failed: {step.error}",
                        "plan": plan.to_dict(),
                    }
            
            plan.complete()
            return {
                "success": True,
                "plan": plan.to_dict(),
                "progress": plan.get_progress(),
            }
        
        except Exception as e:
            plan.fail()
            return {
                "success": False,
                "error": str(e),
                "plan": plan.to_dict(),
            }
    
    def should_create_plan(self, message: str) -> bool:
        """
        Determine if a message requires a plan.
        
        Simple heuristic - complex or multi-step requests need plans.
        """
        # Indicators that a plan might be needed
        plan_indicators = [
            "then",
            "after that",
            "next",
            "finally",
            "step by step",
            "plan",
            "build",
            "create a",
            "implement",
            "develop",
        ]
        
        message_lower = message.lower()
        
        # Check for plan indicators
        if any(indicator in message_lower for indicator in plan_indicators):
            return True
        
        # Check for complex requests (longer messages)
        if len(message) > 200:
            return True
        
        # Check for multiple verbs/actions
        action_words = ["create", "build", "write", "analyze", "search", "calculate", "generate"]
        action_count = sum(1 for word in action_words if word in message_lower)
        if action_count >= 2:
            return True
        
        return False
    
    def detect_task_type(self, message: str) -> Optional[str]:
        """Detect the task type for template selection"""
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in ["document", "pdf", "file", "read"]):
            return "document_analysis"
        elif any(keyword in message_lower for keyword in ["code", "function", "implement", "program"]):
            return "code_generation"
        elif any(keyword in message_lower for keyword in ["research", "find", "look up", "investigate"]):
            return "research_task"
        elif any(keyword in message_lower for keyword in ["data", "analyze", "statistics", "dataset"]):
            return "data_analysis"
        
        return None
