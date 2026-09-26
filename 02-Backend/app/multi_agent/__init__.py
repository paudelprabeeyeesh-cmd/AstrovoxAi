import importlib.util
import os

_multi_agent_path = os.path.join(os.path.dirname(__file__), "..", "multi_agent.py")
_spec = importlib.util.spec_from_file_location("app._multi_agent_module", _multi_agent_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

collaboration_manager = _mod.collaboration_manager
agent_orchestrator = _mod.agent_orchestrator
PlannerAgent = _mod.PlannerAgent
ResearcherAgent = _mod.ResearcherAgent
CoderAgent = _mod.CoderAgent
ReviewerAgent = _mod.ReviewerAgent
SecurityAgent = _mod.SecurityAgent
AgentRole = _mod.AgentRole
TaskStatus = _mod.TaskStatus
