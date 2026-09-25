import logging
from dataclasses import dataclass, field
from typing import Any

from ...config import settings

logger = logging.getLogger(__name__)


@dataclass
class Proposal:
    id: str
    agent: str
    content: str
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentDebate:
    def __init__(self, proposal: Proposal, agents: list[str]):
        self.proposal = proposal
        self.agents = agents
        self.rounds: list[dict[str, str]] = []

    def run(self, llm_client: Any | None = None) -> dict[str, Any]:
        client = llm_client or self._get_openai()
        for agent in self.agents:
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini-2024-07-18",
                    messages=[
                        {"role": "system", "content": f"You are {agent}. Critique or support the following proposal."},
                        {"role": "user", "content": self.proposal.content},
                    ],
                    temperature=0.4,
                )
                self.rounds.append({"agent": agent, "content": response.choices[0].message.content or ""})
            except Exception as e:
                logger.error(f"Debate round failed for {agent}: {e}")
                self.rounds.append({"agent": agent, "content": "", "error": str(e)})
        return {"proposal_id": self.proposal.id, "rounds": self.rounds}

    def _get_openai(self):
        import openai
        return openai.OpenAI(api_key=settings.OPENAI_API_KEY)


class DebateEngine:
    def __init__(self, llm_client: Any | None = None):
        self.llm = llm_client
        self._openai = None

    def _get_openai(self):
        if self._openai is None:
            import openai
            self._openai = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai

    def round(self, proposal: str, agents: list[str]) -> dict[str, Any]:
        prop = Proposal(id="p1", agent="user", content=proposal)
        debate = AgentDebate(proposal=prop, agents=agents)
        return debate.run(self.llm or self._get_openai())

    def vote(self, proposals: list[Proposal], agents: list[str]) -> dict[str, Any]:
        client = self.llm or self._get_openai()
        votes: dict[str, dict[str, str]] = {}
        for agent in agents:
            votes[agent] = {}
            for p in proposals:
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini-2024-07-18",
                        messages=[
                            {"role": "system", "content": f"You are {agent}. Vote approve or reject and explain briefly."},
                            {"role": "user", "content": p.content},
                        ],
                        temperature=0.2,
                    )
                    votes[agent][p.id] = response.choices[0].message.content or ""
                except Exception as e:
                    logger.error(f"Voting failed for {agent} on {p.id}: {e}")
                    votes[agent][p.id] = ""
        return votes

    def consensus(self, proposals: list[Proposal], votes: dict[str, dict[str, str]]) -> Proposal:
        scores: dict[str, float] = {p.id: 0.0 for p in proposals}
        for agent_votes in votes.values():
            for pid, text in agent_votes.items():
                if "approve" in text.lower():
                    scores[pid] = scores.get(pid, 0.0) + 1.0
                elif "reject" in text.lower():
                    scores[pid] = scores.get(pid, 0.0) - 1.0
        best_id = max(scores, key=lambda k: scores[k])
        best = next((p for p in proposals if p.id == best_id), proposals[0])
        best.score = scores.get(best.id, 0.0)
        return best
