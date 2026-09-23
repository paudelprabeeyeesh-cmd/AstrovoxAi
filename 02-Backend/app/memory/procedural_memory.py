"""
Procedural Memory - Phase 3.2 Layer 5

Stores recurring workflows and procedures:
- "Generate release notes"
- "Create API documentation"
- "Summarize meeting"
- "Review pull request"

Instead of repeating instructions, Astrovox can execute stored procedures.
"""

from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum
import json


class ProcedureStatus(Enum):
    """Status of a procedure"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DRAFT = "draft"


class ProcedureStep:
    """Represents a single step in a procedure"""
    
    def __init__(
        self,
        step_id: int,
        description: str,
        action: str,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        self.step_id = step_id
        self.description = description
        self.action = action
        self.parameters = parameters or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary"""
        return {
            "step_id": self.step_id,
            "description": self.description,
            "action": self.action,
            "parameters": self.parameters,
        }


class Procedure:
    """Represents a stored procedure/workflow"""
    
    def __init__(
        self,
        procedure_id: str,
        name: str,
        description: str,
        steps: List[ProcedureStep],
        category: str = "general",
        status: ProcedureStatus = ProcedureStatus.ACTIVE,
    ):
        self.procedure_id = procedure_id
        self.name = name
        self.description = description
        self.steps = steps
        self.category = category
        self.status = status
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()
        self.usage_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert procedure to dictionary"""
        return {
            "procedure_id": self.procedure_id,
            "name": self.name,
            "description": self.description,
            "steps": [step.to_dict() for step in self.steps],
            "category": self.category,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "usage_count": self.usage_count,
        }
    
    def execute(self, executor: Callable) -> Dict[str, Any]:
        """Execute the procedure"""
        results = []
        
        for step in self.steps:
            try:
                result = executor(step.action, step.parameters)
                results.append({
                    "step_id": step.step_id,
                    "success": True,
                    "result": result,
                })
            except Exception as e:
                results.append({
                    "step_id": step.step_id,
                    "success": False,
                    "error": str(e),
                })
        
        self.usage_count += 1
        self.updated_at = datetime.utcnow().isoformat()
        
        return {
            "procedure_id": self.procedure_id,
            "success": all(r["success"] for r in results),
            "results": results,
        }


class ProceduralMemory:
    """
    Stores and manages recurring workflows and procedures.
    Enables the AI to remember and execute complex multi-step processes.
    """
    
    def __init__(self):
        self.procedures: Dict[str, Procedure] = {}
        self.next_procedure_id = 1
        self._initialize_default_procedures()
    
    def _initialize_default_procedures(self):
        """Initialize some default procedures"""
        
        # Release notes generation
        self.create_procedure(
            name="Generate Release Notes",
            description="Generate release notes from recent changes",
            steps=[
                ProcedureStep(1, "Get recent commits", "get_commits", {"limit": 20}),
                ProcedureStep(2, "Parse commit messages", "parse_commits", {}),
                ProcedureStep(3, "Categorize changes", "categorize_changes", {}),
                ProcedureStep(4, "Generate summary", "generate_summary", {}),
                ProcedureStep(5, "Format as markdown", "format_markdown", {}),
            ],
            category="development",
        )
        
        # Meeting summary
        self.create_procedure(
            name="Summarize Meeting",
            description="Create a summary from meeting notes",
            steps=[
                ProcedureStep(1, "Extract key points", "extract_key_points", {}),
                ProcedureStep(2, "Identify action items", "identify_actions", {}),
                ProcedureStep(3, "List participants", "list_participants", {}),
                ProcedureStep(4, "Generate summary", "generate_summary", {}),
                ProcedureStep(5, "Create follow-up tasks", "create_tasks", {}),
            ],
            category="productivity",
        )
        
        # Code review
        self.create_procedure(
            name="Review Pull Request",
            description="Review a pull request systematically",
            steps=[
                ProcedureStep(1, "Get PR diff", "get_diff", {}),
                ProcedureStep(2, "Analyze changes", "analyze_changes", {}),
                ProcedureStep(3, "Check for issues", "check_issues", {}),
                ProcedureStep(4, "Review tests", "review_tests", {}),
                ProcedureStep(5, "Generate feedback", "generate_feedback", {}),
            ],
            category="development",
        )
    
    def create_procedure(
        self,
        name: str,
        description: str,
        steps: List[ProcedureStep],
        category: str = "general",
        status: ProcedureStatus = ProcedureStatus.ACTIVE,
    ) -> str:
        """
        Create a new procedure.
        
        Args:
            name: Procedure name
            description: Procedure description
            steps: List of procedure steps
            category: Procedure category
            status: Procedure status
        
        Returns:
            Procedure ID
        """
        procedure_id = f"proc_{self.next_procedure_id}"
        self.next_procedure_id += 1
        
        procedure = Procedure(
            procedure_id=procedure_id,
            name=name,
            description=description,
            steps=steps,
            category=category,
            status=status,
        )
        
        self.procedures[procedure_id] = procedure
        return procedure_id
    
    def get_procedure(self, procedure_id: str) -> Optional[Dict[str, Any]]:
        """Get a procedure by ID"""
        procedure = self.procedures.get(procedure_id)
        if procedure:
            return procedure.to_dict()
        return None
    
    def get_procedures_by_category(
        self,
        category: str,
        status: Optional[ProcedureStatus] = None,
    ) -> List[Dict[str, Any]]:
        """Get procedures by category"""
        procedures = [
            proc for proc in self.procedures.values()
            if proc.category == category
        ]
        
        if status:
            procedures = [proc for proc in procedures if proc.status == status]
        
        return [proc.to_dict() for proc in procedures]
    
    def get_all_procedures(
        self,
        status: Optional[ProcedureStatus] = None,
    ) -> List[Dict[str, Any]]:
        """Get all procedures, optionally filtered by status"""
        procedures = list(self.procedures.values())
        
        if status:
            procedures = [proc for proc in procedures if proc.status == status]
        
        return [proc.to_dict() for proc in procedures]
    
    def update_procedure(
        self,
        procedure_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        steps: Optional[List[ProcedureStep]] = None,
        status: Optional[ProcedureStatus] = None,
    ):
        """Update a procedure"""
        procedure = self.procedures.get(procedure_id)
        if not procedure:
            return
        
        if name is not None:
            procedure.name = name
        if description is not None:
            procedure.description = description
        if steps is not None:
            procedure.steps = steps
        if status is not None:
            procedure.status = status
        
        procedure.updated_at = datetime.utcnow().isoformat()
    
    def delete_procedure(self, procedure_id: str):
        """Delete a procedure"""
        if procedure_id in self.procedures:
            del self.procedures[procedure_id]
    
    def execute_procedure(
        self,
        procedure_id: str,
        executor: Callable,
    ) -> Dict[str, Any]:
        """
        Execute a procedure.
        
        Args:
            procedure_id: Procedure ID
            executor: Function to execute individual steps
        
        Returns:
            Execution results
        """
        procedure = self.procedures.get(procedure_id)
        if not procedure:
            return {
                "success": False,
                "error": "Procedure not found",
            }
        
        return procedure.execute(executor)
    
    def search_procedures(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search procedures by name or description"""
        query_lower = query.lower()
        results = []
        
        for procedure in self.procedures.values():
            if query_lower in procedure.name.lower() or query_lower in procedure.description.lower():
                results.append(procedure.to_dict())
        
        return results[:limit]
    
    def get_most_used(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most frequently used procedures"""
        procedures = list(self.procedures.values())
        procedures.sort(key=lambda p: p.usage_count, reverse=True)
        return [proc.to_dict() for proc in procedures[:limit]]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of procedural memory"""
        by_category = {}
        by_status = {}
        
        for procedure in self.procedures.values():
            # Count by category
            if procedure.category not in by_category:
                by_category[procedure.category] = 0
            by_category[procedure.category] += 1
            
            # Count by status
            status = procedure.status.value
            if status not in by_status:
                by_status[status] = 0
            by_status[status] += 1
        
        total_executions = sum(proc.usage_count for proc in self.procedures.values())
        
        return {
            "total_procedures": len(self.procedures),
            "by_category": by_category,
            "by_status": by_status,
            "total_executions": total_executions,
            "most_used": self.get_most_used(3),
        }
