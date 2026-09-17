class AgentCollaboration:
    def __init__(self):
        self.agents = {}

    def register(self, agent_id, agent):
        self.agents[agent_id] = agent

    def delegate(self, from_agent, to_agent, task):
        if to_agent not in self.agents:
            raise ValueError(f"Agent {to_agent} not found")
        return self.agents[to_agent].execute(task)

    def broadcast(self, from_agent, task):
        results = {}
        for agent_id, agent in self.agents.items():
            if agent_id != from_agent:
                results[agent_id] = agent.execute(task)
        return results
