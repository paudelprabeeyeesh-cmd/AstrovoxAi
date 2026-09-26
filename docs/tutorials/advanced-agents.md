# Advanced Agents Tutorial

This tutorial covers building advanced autonomous agents with AstrovoxAI.

## Prerequisites

- Completed [Getting Started](../tutorials/getting-started.md)
- Python 3.9+
- Understanding of async programming

## Building a Research Agent

```python
from ASTROVOX_AI.ai_core.autonomous_agents.agent_runtime import AgentRuntime, Tool

def search_web(query: str) -> str:
    """Search the web for information."""
    return f"Search results for: {query}"

def execute_code(code: str) -> str:
    """Execute Python code in a sandbox."""
    return f"Executed: {code}"

agent = AgentRuntime(
    name="research_agent",
    llm_client=llm,
    tools=[
        Tool(name="search_web", description="Search the web", func=search_web),
        Tool(name="execute_code", description="Run Python code", func=execute_code)
    ],
    max_iterations=10,
    temperature=0.7
)

result = agent.run("Research the latest AI safety papers and summarize findings")
print(result)
```

## Multi-Agent Systems

```python
from ASTROVOX_AI.ai_core.autonomous_agents.multi_agent import (
    Agent,
    MultiAgentOrchestrator,
)

orchestrator = MultiAgentOrchestrator()
orchestrator.register(Agent(
    name="planner",
    runtime=planner_runtime,
    description="Breaks down complex tasks into steps"
))
orchestrator.register(Agent(
    name="researcher",
    runtime=researcher_runtime,
    description="Gathers information from various sources"
))

results = orchestrator.run_round("Build a web scraper for news sites")
```

## Next Steps

- Read the [Agents Documentation](../docs/AGENTS.md)
- Explore the [Extension Framework](../docs/extension-framework.md)
- Try the [API Playground](../docs/API_PLAYGROUND.md)
