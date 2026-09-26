# Autonomous Agents

AstrovoxAI provides a comprehensive agent framework for building autonomous AI systems with tool use, memory, planning, and safety guarantees.

## Architecture
- **Agent Runtime**: Tool use, memory, planning loop
- **World Model**: Environment modeling and prediction
- **Safety Layer**: Action validation, sanitization, rate limiting
- **Multi-Agent Orchestrator**: Agent registration, handoff, round-robin execution

## Usage
```python
from ASTROVOX_AI.ai_core.autonomous_agents.agent_runtime import AgentRuntime, Tool

def search_web(query: str) -> str:
    return f"Search results for: {query}"

agent = AgentRuntime(
    name="research_agent",
    llm_client=llm,
    tools=[Tool(name="search_web", description="Search the web", func=search_web)]
)
result = agent.run("Research the latest AI safety papers")
```

## Multi-Agent
```python
from ASTROVOX_AI.ai_core.autonomous_agents.multi_agent import Agent, MultiAgentOrchestrator

orchestrator = MultiAgentOrchestrator()
orchestrator.register(Agent("planner", planner_runtime))
orchestrator.register(Agent("researcher", researcher_runtime))
orchestrator.register(Agent("coder", coder_runtime))
results = orchestrator.run_round("Build a web scraper")
```

## Safety
```python
from ASTROVOX_AI.ai_core.autonomous_agents.safety_layer import SafetyLayer

safety = SafetyLayer()
safety.add_blocklist("delete")
safety.add_blocklist("shutdown")
ok, reason = safety.validate_action({"action": "read_file"}, {})
```
