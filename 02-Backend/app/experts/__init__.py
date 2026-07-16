"""
Astrovox AI Expert Ecosystem
Phase 4: Expert AI System Implementation

This module provides specialized Expert AI Systems for different domains:
- Education AI
- Medical AI
- Programming AI
- Trading & Finance AI
- Cybersecurity AI
- Legal AI
- Business AI
- Research AI
- Creative AI
- Language AI
- Engineering AI
- Data Science AI
- Productivity AI

Also includes:
- Universal AI Router for automatic expert selection
- AI Collaboration System for multi-expert tasks
- Project Mode for persistent workspaces
"""

from .expert_base import ExpertBase, ExpertProfile, ExpertCapabilities
from .universal_router import UniversalRouter, RoutingDecision
from .expert_collaboration import ExpertCollaborator, CollaborationPlan
from .project_mode import ProjectManager, ProjectWorkspace

__all__ = [
    "ExpertBase",
    "ExpertProfile", 
    "ExpertCapabilities",
    "UniversalRouter",
    "RoutingDecision",
    "ExpertCollaborator",
    "CollaborationPlan",
    "ProjectManager",
    "ProjectWorkspace",
]
