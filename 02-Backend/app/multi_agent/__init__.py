import importlib.util
import os

_multi_agent_path = os.path.join(os.path.dirname(__file__), "..", "multi_agent.py")
_spec = importlib.util.spec_from_file_location("app._multi_agent_module", os.path.abspath(_multi_agent_path))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

Agent = _mod.Agent
AgentConfig = _mod.AgentConfig
AgentRole = _mod.AgentRole
AgentState = _mod.AgentState
TaskStatus = _mod.TaskStatus
PermissionLevel = _mod.PermissionLevel
AgentCapability = _mod.AgentCapability
AgentHealth = _mod.AgentHealth
AgentMetadata = _mod.AgentMetadata
AgentTask = _mod.AgentTask
AgentMessage = _mod.AgentMessage
CollaborationSession = _mod.CollaborationSession
AgentRegistry = _mod.AgentRegistry
AgentOrchestrator = _mod.AgentOrchestrator
CollaborationManager = _mod.CollaborationManager
PlannerAgent = _mod.PlannerAgent
ResearcherAgent = _mod.ResearcherAgent
CoderAgent = _mod.CoderAgent
ReviewerAgent = _mod.ReviewerAgent
SecurityAgent = _mod.SecurityAgent
collaboration_manager = _mod.collaboration_manager
agent_orchestrator = _mod.agent_orchestrator
