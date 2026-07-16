"""
Expert Collaboration System - Phase 4.4

Coordinates multiple Expert AI Systems for complex tasks that require
domain expertise from multiple areas.

Example: "Build a hospital management system"
- Programming AI (for code)
- Medical AI (for domain knowledge)
- Database AI (for data structure)
- UI/UX AI (for interface)
- Security AI (for security)
- Testing AI (for quality assurance)
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from .expert_base import ExpertBase


class CollaborationPhase(Enum):
    """Phases of collaboration"""
    PLANNING = "planning"
    EXECUTION = "execution"
    INTEGRATION = "integration"
    REVIEW = "review"


@dataclass
class ExpertTask:
    """A task assigned to an expert"""
    expert_id: str
    task_description: str
    dependencies: List[str] = field(default_factory=list)
    priority: int = 1
    estimated_duration: int = 60  # seconds
    status: str = "pending"
    result: Optional[Any] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class CollaborationPlan:
    """Plan for expert collaboration"""
    plan_id: str
    goal: str
    experts: List[str]
    tasks: List[ExpertTask]
    phases: List[CollaborationPhase]
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = "pending"
    coordinator: Optional[str] = None


class ExpertCollaborator:
    """
    Coordinates collaboration between multiple Expert AI Systems.
    Acts as the coordinator that combines outputs and resolves conflicts.
    """
    
    def __init__(self):
        self.plans: Dict[str, CollaborationPlan] = {}
        self.active_collaborations: Dict[str, CollaborationPlan] = {}
        self.next_plan_id = 1
    
    def create_collaboration_plan(
        self,
        goal: str,
        expert_ids: List[str],
        task_descriptions: Dict[str, str],
        dependencies: Optional[Dict[str, List[str]]] = None,
    ) -> CollaborationPlan:
        """
        Create a collaboration plan for multi-expert task.
        
        Args:
            goal: Overall goal of the collaboration
            expert_ids: List of expert IDs to involve
            task_descriptions: Task for each expert (expert_id -> description)
            dependencies: Task dependencies (expert_id -> list of expert_ids to wait for)
        
        Returns:
            Collaboration plan
        """
        plan_id = f"collab_{self.next_plan_id}"
        self.next_plan_id += 1
        
        # Create tasks
        tasks = []
        for expert_id in expert_ids:
            task = ExpertTask(
                expert_id=expert_id,
                task_description=task_descriptions.get(expert_id, "Contribute to goal"),
                dependencies=dependencies.get(expert_id, []),
            )
            tasks.append(task)
        
        # Define phases
        phases = [
            CollaborationPhase.PLANNING,
            CollaborationPhase.EXECUTION,
            CollaborationPhase.INTEGRATION,
            CollaborationPhase.REVIEW,
        ]
        
        plan = CollaborationPlan(
            plan_id=plan_id,
            goal=goal,
            experts=expert_ids,
            tasks=tasks,
            phases=phases,
        )
        
        self.plans[plan_id] = plan
        return plan
    
    def execute_collaboration(
        self,
        plan_id: str,
        experts: Dict[str, ExpertBase],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a collaboration plan.
        
        Args:
            plan_id: Plan ID
            experts: Dictionary of expert_id -> ExpertBase
            context: Additional context
        
        Returns:
            Collaboration results
        """
        plan = self.plans.get(plan_id)
        if not plan:
            return {"success": False, "error": "Plan not found"}
        
        plan.status = "in_progress"
        self.active_collaborations[plan_id] = plan
        
        try:
            # Phase 1: Planning
            plan.phases[0]  # Mark as current phase
            
            # Phase 2: Execution
            plan.phases[1]
            execution_results = self._execute_tasks(plan, experts, context)
            
            # Phase 3: Integration
            plan.phases[2]
            integrated_result = self._integrate_results(execution_results, plan)
            
            # Phase 4: Review
            plan.phases[3]
            review_result = self._review_collaboration(integrated_result, plan)
            
            plan.status = "completed"
            del self.active_collaborations[plan_id]
            
            return {
                "success": True,
                "plan_id": plan_id,
                "goal": plan.goal,
                "execution_results": execution_results,
                "integrated_result": integrated_result,
                "review": review_result,
            }
        
        except Exception as e:
            plan.status = "failed"
            del self.active_collaborations[plan_id]
            
            return {
                "success": False,
                "error": str(e),
                "plan_id": plan_id,
            }
    
    def _execute_tasks(
        self,
        plan: CollaborationPlan,
        experts: Dict[str, ExpertBase],
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute tasks respecting dependencies"""
        results = {}
        completed_tasks = set()
        
        # Execute tasks in dependency order
        while len(completed_tasks) < len(plan.tasks):
            progress_made = False
            
            for task in plan.tasks:
                if task.expert_id in completed_tasks:
                    continue
                
                # Check if dependencies are satisfied
                dependencies_satisfied = all(
                    dep in completed_tasks for dep in task.dependencies
                )
                
                if dependencies_satisfied:
                    # Execute task
                    expert = experts.get(task.expert_id)
                    if not expert:
                        results[task.expert_id] = {
                            "success": False,
                            "error": "Expert not available",
                        }
                    else:
                        task.status = "in_progress"
                        task.started_at = datetime.utcnow().isoformat()
                        
                        result = expert.process_request(
                            user_message=task.task_description,
                            context=context,
                        )
                        
                        task.result = result
                        task.status = "completed"
                        task.completed_at = datetime.utcnow().isoformat()
                        
                        results[task.expert_id] = result
                    
                    completed_tasks.add(task.expert_id)
                    progress_made = True
            
            if not progress_made:
                # Circular dependency or missing expert
                break
        
        return results
    
    def _integrate_results(
        self,
        execution_results: Dict[str, Any],
        plan: CollaborationPlan,
    ) -> Dict[str, Any]:
        """Integrate results from multiple experts"""
        integrated = {
            "goal": plan.goal,
            "expert_contributions": {},
            "conflicts": [],
            "recommendations": [],
        }
        
        # Collect contributions
        for expert_id, result in execution_results.items():
            if result.get("success"):
                integrated["expert_contributions"][expert_id] = {
                    "expert_id": expert_id,
                    "response": result.get("response", ""),
                    "confidence": result.get("confidence", 0.0),
                }
        
        # Detect conflicts (simplified)
        # In production, this would use more sophisticated conflict detection
        if len(integrated["expert_contributions"]) > 1:
            # Check for contradictory recommendations
            integrated["conflicts"] = self._detect_conflicts(integrated["expert_contributions"])
        
        # Generate integration recommendations
        integrated["recommendations"] = self._generate_integration_recommendations(
            integrated["expert_contributions"]
        )
        
        return integrated
    
    def _detect_conflicts(self, contributions: Dict[str, Any]) -> List[str]:
        """Detect conflicts between expert contributions"""
        conflicts = []
        
        # Simplified conflict detection
        # In production, this would analyze the actual content
        responses = list(contributions.values())
        
        if len(responses) >= 2:
            # Check for very different confidence levels
            confidences = [r["confidence"] for r in responses]
            if max(confidences) - min(confidences) > 0.5:
                conflicts.append("Significant confidence difference between experts")
        
        return conflicts
    
    def _generate_integration_recommendations(self, contributions: Dict[str, Any]) -> List[str]:
        """Generate recommendations for integrating expert outputs"""
        recommendations = []
        
        if len(contributions) == 1:
            recommendations.append("Single expert contribution - use as-is")
        else:
            recommendations.append("Combine expert inputs using weighted averaging")
            recommendations.append("Prioritize higher-confidence contributions")
            recommendations.append("Review conflicts and resolve manually if needed")
        
        return recommendations
    
    def _review_collaboration(
        self,
        integrated_result: Dict[str, Any],
        plan: CollaborationPlan,
    ) -> Dict[str, Any]:
        """Review the collaboration result"""
        review = {
            "plan_id": plan.plan_id,
            "total_experts": len(plan.experts),
            "successful_contributions": len(integrated_result["expert_contributions"]),
            "conflicts_detected": len(integrated_result["conflicts"]),
            "overall_quality": self._assess_quality(integrated_result),
            "recommendations": integrated_result["recommendations"],
        }
        
        return review
    
    def _assess_quality(self, integrated_result: Dict[str, Any]) -> str:
        """Assess the quality of collaboration result"""
        successful = len(integrated_result["expert_contributions"])
        conflicts = len(integrated_result["conflicts"])
        
        if successful == 0:
            return "failed"
        elif conflicts > 0:
            return "needs_review"
        elif successful >= 2:
            return "excellent"
        else:
            return "good"
    
    def get_plan(self, plan_id: str) -> Optional[CollaborationPlan]:
        """Get a collaboration plan"""
        return self.plans.get(plan_id)
    
    def get_active_collaborations(self) -> List[Dict[str, Any]]:
        """Get currently active collaborations"""
        return [
            {
                "plan_id": plan.plan_id,
                "goal": plan.goal,
                "experts": plan.experts,
                "status": plan.status,
            }
            for plan in self.active_collaborations.values()
        ]
    
    def cancel_collaboration(self, plan_id: str) -> bool:
        """Cancel an active collaboration"""
        if plan_id in self.active_collaborations:
            plan = self.active_collaborations[plan_id]
            plan.status = "cancelled"
            del self.active_collaborations[plan_id]
            return True
        return False
