# Autonomous Agents

AstrovoxAI provides a comprehensive agent framework for building autonomous AI systems with tool use, memory, planning, safety guarantees, and multi-agent collaboration.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT FRAMEWORK                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │   Agent      │    │   Tool       │    │   Memory         │  │
│  │   Runtime    │◄──►│   Registry   │    │   Store          │  │
│  └──────┬───────┘    └──────────────┘    └──────────────────┘  │
│         │                                                       │
│  ┌──────▼───────────────────────────────────────────────────┐  │
│  │                  Planning & Reasoning Loop                 │  │
│  │  Observe → Reason → Plan → Act → Reflect → Learn          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │   Safety     │    │   World      │    │   Multi-Agent    │  │
│  │   Layer      │    │   Model      │    │   Orchestrator   │  │
│  └──────────────┘    └──────────────┘    └──────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

| Component | Responsibility |
|-----------|----------------|
| Agent Runtime | Tool execution, memory access, planning loop |
| Tool Registry | Dynamic tool registration, discovery, and validation |
| Memory Store | Short-term and long-term memory with importance weighting |
| Planning Engine | Task decomposition, step generation, dependency resolution |
| Safety Layer | Action validation, sanitization, rate limiting, guardrails |
| World Model | Environment modeling, state prediction, consequence analysis |
| Multi-Agent Orchestrator | Agent registration, handoff, round-robin, swarm execution |

## Single Agent Usage

```python
from ASTROVOX_AI.ai_core.autonomous_agents.agent_runtime import AgentRuntime, Tool

def search_web(query: str) -> str:
    """Search the web for information."""
    return f"Search results for: {query}"

def execute_code(code: str) -> str:
    """Execute Python code in a sandbox."""
    # Sandboxed execution logic
    pass

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

### Agent Runtime Features

- **Iterative execution**: Agents can plan and execute multiple steps
- **Tool chaining**: Output of one tool feeds into the next
- **Error recovery**: Automatic retry with fallback strategies
- **Memory integration**: Agents remember past interactions
- **Context management**: Automatic prompt windowing and summarization

## Multi-Agent Systems

```python
from ASTROVOX_AI.ai_core.autonomous_agents.multi_agent import (
    Agent,
    MultiAgentOrchestrator,
    SwarmOrchestrator
)

orchestrator = MultiAgentOrchestrator()

# Register specialized agents
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

orchestrator.register(Agent(
    name="coder",
    runtime=coder_runtime,
    description="Writes and debugs code"
))

orchestrator.register(Agent(
    name="reviewer",
    runtime=reviewer_runtime,
    description="Reviews and improves outputs"
))

# Round-robin execution
results = orchestrator.run_round("Build a web scraper for news sites")

# Swarm execution for parallel tasks
swarm = SwarmOrchestrator()
swarm_results = swarm.run_parallel([
    "Research competitor pricing",
    "Analyze market trends",
    "Draft marketing copy"
])
```

### Orchestration Patterns

| Pattern | Description | Use Case |
|---------|-------------|----------|
| Sequential | Agents execute one after another | Pipeline workflows |
| Parallel | Agents execute simultaneously | Independent research tasks |
| Hierarchical | Manager agent delegates to workers | Complex multi-step tasks |
| Swarm | Peer-to-peer agent collaboration | Creative brainstorming |

## Safety Layer

```python
from ASTROVOX_AI.ai_core.autonomous_agents.safety_layer import (
    SafetyLayer,
    ActionValidator,
    ContentFilter
)

safety = SafetyLayer()

# Block dangerous actions
safety.add_blocklist("delete")
safety.add_blocklist("shutdown")
safety.add_blocklist("format")

# Add allowlist for permitted actions
safety.add_allowlist("read")
safety.add_allowlist("write")
safety.add_allowlist("search")

# Rate limit tools
safety.set_rate_limit("web_search", max_calls=10, window_seconds=60)

# Validate actions before execution
ok, reason = safety.validate_action(
    {"action": "read_file", "path": "/tmp/data.txt"},
    context={"user_role": "admin"}
)

if not ok:
    raise PermissionError(f"Action blocked: {reason}")
```

### Safety Features

- **Action validation**: All tool calls validated against policies
- **Input sanitization**: Prevent injection attacks in tool parameters
- **Rate limiting**: Per-tool and per-agent rate limits
- **Audit logging**: All actions logged for compliance
- **Permission enforcement**: RBAC integration for tool access

## Tool Development

```python
from ASTROVOX_AI.ai_core.autonomous_agents.tool_registry import tool, ToolParameter

@tool(
    name="calculate_compound_interest",
    description="Calculate compound interest over time",
    parameters=[
        ToolParameter(name="principal", type="float", description="Initial amount"),
        ToolParameter(name="rate", type="float", description="Annual interest rate (decimal)"),
        ToolParameter(name="time", type="int", description="Time in years"),
        ToolParameter(name="compound_frequency", type="int", description="Compounds per year", default=12)
    ]
)
def calculate_compound_interest(principal: float, rate: float, time: int, compound_frequency: int = 12) -> dict:
    """Calculate compound interest with given parameters."""
    amount = principal * (1 + rate / compound_frequency) ** (compound_frequency * time)
    return {
        "principal": principal,
        "final_amount": round(amount, 2),
        "interest_earned": round(amount - principal, 2)
    }
```

### Tool Categories

| Category | Examples | Description |
|----------|----------|-------------|
| Retrieval | web_search, database_query | Fetch data from external sources |
| Computation | calculator, code_execution | Perform calculations or run code |
| Creation | file_write, email_send | Create or send content |
| Analysis | sentiment_analysis, data_analysis | Analyze and summarize data |
| Integration | calendar, crm, slack | Connect to external services |

## Memory Integration

Agents have access to persistent memory:

```python
from ASTROVOX_AI.ai_core.autonomous_agents.memory import AgentMemory

memory = AgentMemory(agent_id="research_agent")

# Store experiences
memory.store("user_preference", {"theme": "dark", "language": "en"})
memory.store("past_task", {"task": "web scraper", "status": "completed"})

# Recall relevant memories
relevant = memory.retrieve("web development", k=5)

# Memory is automatically injected into agent prompts
```

## World Model

```python
from ASTROVOX_AI.ai_core.autonomous_agents.world_model import WorldModel

world_model = WorldModel()

# Define environment states
world_model.add_state("file_exists", {"path": "/tmp/data.txt"})
world_model.add_state("user_logged_in", {"user_id": "123"})

# Predict action outcomes
outcome = world_model.predict(
    action={"type": "write_file", "path": "/tmp/data.txt"},
    current_state={"file_exists": False}
)

# Learn from experience
world_model.update(
    action={"type": "write_file"},
    outcome={"success": True, "bytes_written": 1024}
)
```

## Performance & Monitoring

- Agent execution time tracking
- Tool call success rates
- Memory hit/miss rates
- Safety violation logs
- Multi-agent coordination overhead

## API Reference

### REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/agents` | List all registered agents |
| GET | `/api/v1/agents/{role}` | Get agent details |
| GET | `/api/v1/agents/{role}/health` | Agent health status |
| POST | `/api/v1/agents/{role}/run` | Execute agent task |
| POST | `/api/v1/agents/tools/register` | Register a new tool |
| DELETE | `/api/v1/agents/tools/{name}` | Unregister a tool |
| GET | `/api/v1/agents/executions` | List agent execution history |
