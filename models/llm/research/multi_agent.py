from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# 1. Agent Communication
# ---------------------------------------------------------------------------


class AgentCommunicationBus:
    """Message bus for inter-agent communication."""

    def __init__(self):
        self.messages: list[dict] = []
        self.subscribers: dict[str, list[callable]] = {}

    def send(self, sender: str, receiver: str, message: dict) -> None:
        msg = {"sender": sender, "receiver": receiver, "content": message, "timestamp": len(self.messages)}
        self.messages.append(msg)
        for sub in self.subscribers.get(receiver, []):
            sub(msg)

    def broadcast(self, sender: str, message: dict) -> None:
        msg = {"sender": sender, "receiver": "all", "content": message, "timestamp": len(self.messages)}
        self.messages.append(msg)
        for subs in self.subscribers.values():
            for sub in subs:
                sub(msg)

    def subscribe(self, agent_id: str, callback: callable) -> None:
        if agent_id not in self.subscribers:
            self.subscribers[agent_id] = []
        self.subscribers[agent_id].append(callback)

    def get_history(self, last_n: int = 10) -> list[dict]:
        return self.messages[-last_n:]


# ---------------------------------------------------------------------------
# 2. Task Decomposition
# ---------------------------------------------------------------------------


class TaskDecomposer(nn.Module):
    """Neural task decomposition into subtasks."""

    def __init__(
        self,
        vocab_size: int = 32000,
        hidden_size: int = 768,
        num_layers: int = 4,
        num_attention_heads: int = 12,
        max_subtasks: int = 8,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.max_subtasks = max_subtasks
        self.embedding = nn.Embedding(vocab_size, hidden_size, device=device, dtype=dtype)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_size, nhead=num_attention_heads, batch_first=True,
            device=device, dtype=dtype,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.ln = nn.LayerNorm(hidden_size, device=device, dtype=dtype)
        self.subtask_head = nn.Linear(hidden_size, max_subtasks * hidden_size, device=device, dtype=dtype)
        self.dependency_head = nn.Linear(hidden_size, max_subtasks * max_subtasks, device=device, dtype=dtype)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        x = self.embedding(input_ids)
        src_key_padding_mask = (attention_mask == 0) if attention_mask is not None else None
        x = self.encoder(x, src_key_padding_mask=src_key_padding_mask)
        x = self.ln(x)
        if attention_mask is not None:
            lengths = attention_mask.sum(dim=1, keepdim=True)
            pooled = (x * attention_mask.unsqueeze(-1)).sum(dim=1) / lengths.clamp(min=1)
        else:
            pooled = x.mean(dim=1)
        subtasks = self.subtask_head(pooled).view(-1, self.max_subtasks, x.size(-1))
        dependencies = self.dependency_head(pooled).view(-1, self.max_subtasks, self.max_subtasks)
        dependencies = torch.sigmoid(dependencies)
        return subtasks, dependencies


@dataclass
class Subtask:
    id: int
    description: str
    dependencies: list[int] = field(default_factory=list)
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
    result: str | None = None


# ---------------------------------------------------------------------------
# 3. Collaborative Planning
# ---------------------------------------------------------------------------


class CollaborativePlanner(nn.Module):
    """Multi-agent collaborative planning module."""

    def __init__(
        self,
        hidden_size: int = 768,
        num_agents: int = 4,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.num_agents = num_agents
        self.agent_embeddings = nn.Embedding(num_agents, hidden_size, device=device, dtype=dtype)
        self.plan_net = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size, device=device, dtype=dtype),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype),
        )
        self.coordination_net = nn.Sequential(
            nn.Linear(hidden_size * num_agents, hidden_size, device=device, dtype=dtype),
            nn.ReLU(),
            nn.Linear(hidden_size, num_agents, device=device, dtype=dtype),
        )

    def forward(self, task_embedding: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        B = task_embedding.size(0)
        agent_embs = self.agent_embeddings.weight.unsqueeze(0).expand(B, -1, -1)
        task_expanded = task_embedding.unsqueeze(1).expand(-1, self.num_agents, -1)
        combined = torch.cat([task_expanded, agent_embs], dim=-1)
        plans = self.plan_net(combined)
        flat = plans.view(B, -1)
        coordination = self.coordination_net(flat)
        return plans, coordination


class MultiAgentSystem:
    """Multi-agent collaboration system."""

    def __init__(
        self,
        num_agents: int = 4,
        model: nn.Module | None = None,
        tokenizer: object | None = None,
        communication_bus: AgentCommunicationBus | None = None,
        device: torch.device | None = None,
    ):
        self.num_agents = num_agents
        self.model = model
        self.tokenizer = tokenizer
        self.communication_bus = communication_bus or AgentCommunicationBus()
        self.device = device or (next(model.parameters()).device if model else torch.device("cpu"))
        self.planner = CollaborativePlanner(
            hidden_size=768, num_agents=num_agents, device=self.device,
        )

    def assign_tasks(self, task: str) -> list[Subtask]:
        task_emb = self._encode_text(task).mean(dim=1, keepdim=True)
        with torch.no_grad():
            plans, coordination = self.planner(task_emb)
        assignment_weights = F.softmax(coordination, dim=-1)[0]
        subtasks = []
        for i in range(self.num_agents):
            subtasks.append(
                Subtask(
                    id=i,
                    description=f"Agent {i}: {task}",
                    dependencies=[],
                )
            )
        return subtasks

    def run_collaborative(self, prompt: str) -> dict:
        subtasks = self.assign_tasks(prompt)
        results = {}
        for subtask in subtasks:
            if self.model is not None:
                agent_prompt = f"You are Agent {subtask.id}. Task: {subtask.description}"
                inputs = self._encode_text(agent_prompt)
                with torch.no_grad():
                    outputs = self.model.generate(**inputs, max_new_tokens=256)
                subtask.result = self._decode_text(outputs)
                subtask.status = "completed"
            results[subtask.id] = {
                "description": subtask.description,
                "status": subtask.status,
                "result": subtask.result,
            }
            self.communication_bus.send(
                sender=f"agent_{subtask.id}",
                receiver="all",
                message=results[subtask.id],
            )
        return results

    def _encode_text(self, text: str) -> torch.Tensor:
        if self.tokenizer is None:
            return torch.zeros(1, 1, device=self.device, dtype=torch.long)
        if hasattr(self.tokenizer, "encode"):
            return torch.tensor([self.tokenizer.encode(text)], device=self.device, dtype=torch.long)
        return torch.zeros(1, 1, device=self.device, dtype=torch.long)

    def _decode_text(self, outputs: torch.Tensor) -> str:
        if self.tokenizer is None:
            return ""
        if hasattr(self.tokenizer, "decode"):
            return self.tokenizer.decode(outputs[0].tolist())
        return " ".join(str(tok) for tok in outputs[0].tolist())


# ---------------------------------------------------------------------------
# 4. Agent Manager
# ---------------------------------------------------------------------------


class AgentManager:
    """Manage lifecycle of multiple collaborating agents."""

    def __init__(self, num_agents: int = 4, device: torch.device | None = None):
        self.num_agents = num_agents
        self.communication_bus = AgentCommunicationBus()
        self.agents: dict[int, dict] = {}
        self.device = device or torch.device("cpu")

    def register_agent(self, agent_id: int, name: str, capabilities: list[str]) -> None:
        self.agents[agent_id] = {
            "name": name,
            "capabilities": capabilities,
            "status": "idle",
            "history": [],
        }

    def dispatch(self, task: dict, target_agent_id: int | None = None) -> dict:
        if target_agent_id is not None:
            agent_id = target_agent_id
        else:
            agent_id = self._select_agent_for_task(task)
        agent = self.agents.get(agent_id)
        if agent is None:
            return {"error": f"Agent {agent_id} not found"}
        agent["status"] = "busy"
        self.communication_bus.send(sender="manager", receiver=agent["name"], message=task)
        agent["history"].append(task)
        agent["status"] = "idle"
        return {"assigned_to": agent_id, "agent_name": agent["name"]}

    def _select_agent_for_task(self, task: dict) -> int:
        required_capabilities = task.get("required_capabilities", [])
        for agent_id, agent in self.agents.items():
            if all(cap in agent["capabilities"] for cap in required_capabilities):
                return agent_id
        return 0

    def get_status(self) -> dict:
        return {aid: {"name": a["name"], "status": a["status"]} for aid, a in self.agents.items()}
