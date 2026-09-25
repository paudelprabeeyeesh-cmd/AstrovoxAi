"""Agent marketplace with dynamic discovery and capability matching."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentCapability(str, Enum):
    PLANNING = "planning"
    RESEARCH = "research"
    CODING = "coding"
    REVIEW = "review"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    RETRIEVAL = "retrieval"
    DELEGATION = "delegation"
    CRITIC = "critic"
    REFLECTION = "reflection"
    DEBUGGING = "debugging"


@dataclass
class AgentListing:
    agent_id: str
    name: str
    capabilities: List[AgentCapability]
    description: str
    pricing: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "active"
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AgentTransaction:
    transaction_id: str
    requester_id: str
    provider_id: str
    capability: AgentCapability
    price: float
    status: str
    result: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AgentMarketplace:
    """Dynamic discovery and transaction system for agent capabilities."""

    def __init__(self):
        self._agents: Dict[str, AgentListing] = {}
        self._transactions: List[AgentTransaction] = []

    def register(self, listing: AgentListing) -> None:
        self._agents[listing.agent_id] = listing
        logger.info("Agent registered: %s", listing.agent_id)

    def unregister(self, agent_id: str) -> bool:
        return self._agents.pop(agent_id, None) is not None

    def discover(
        self,
        capability: AgentCapability,
        max_price: Optional[float] = None,
    ) -> List[AgentListing]:
        matches = []
        for listing in self._agents.values():
            if listing.status != "active":
                continue
            if capability not in listing.capabilities:
                continue
            price = listing.pricing.get(capability.value, float("inf"))
            if max_price is not None and price > max_price:
                continue
            matches.append(listing)
        matches.sort(key=lambda l: l.pricing.get(capability.value, float("inf")))
        return matches

    def execute_transaction(
        self,
        requester_id: str,
        provider_id: str,
        capability: AgentCapability,
        result: Optional[str] = None,
    ) -> AgentTransaction:
        listing = self._agents.get(provider_id)
        price = listing.pricing.get(capability.value, 0.0) if listing else 0.0
        transaction = AgentTransaction(
            transaction_id=f"txn_{datetime.now(timezone.utc).timestamp()}",
            requester_id=requester_id,
            provider_id=provider_id,
            capability=capability,
            price=price,
            status="completed",
            result=result,
        )
        self._transactions.append(transaction)
        return transaction

    def list_agents(self) -> List[AgentListing]:
        return list(self._agents.values())

    def get_agent(self, agent_id: str) -> Optional[AgentListing]:
        return self._agents.get(agent_id)


_marketplace: Optional[AgentMarketplace] = None


def get_marketplace() -> AgentMarketplace:
    global _marketplace
    if _marketplace is None:
        _marketplace = AgentMarketplace()
    return _marketplace
