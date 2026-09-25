from typing import Optional, Dict, Any, List
from datetime import datetime
from ASTROVOX_AI.ai_core.distributed.distributed_cache import DistributedCache


class AgentMarketplace:
    def __init__(self, cache: Optional[DistributedCache] = None):
        self.cache = cache or DistributedCache(max_size=10000)
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.listings: Dict[str, Dict[str, Any]] = {}
        self.transactions: List[Dict[str, Any]] = []

    def register_agent(self, agent_id: str, capabilities: List[str], pricing: Dict[str, float], metadata: Optional[Dict[str, Any]] = None) -> None:
        self.agents[agent_id] = {'capabilities': capabilities, 'pricing': pricing, 'metadata': metadata or {}, 'registered_at': datetime.now().isoformat(), 'status': 'active'}
        self.cache.set(f'agent:{agent_id}', self.agents[agent_id])

    def list_capability(self, agent_id: str, capability: str, price: float, description: str = '') -> str:
        listing_id = f"listing:{agent_id}:{capability}:{len(self.listings)}"
        self.listings[listing_id] = {'agent_id': agent_id, 'capability': capability, 'price': price, 'description': description, 'created_at': datetime.now().isoformat()}
        self.cache.set(listing_id, self.listings[listing_id])
        return listing_id

    def discover(self, capability: str, max_price: Optional[float] = None) -> List[Dict[str, Any]]:
        matches = []
        for listing_id, listing in self.listings.items():
            if listing.get('capability') == capability:
                if max_price is None or listing.get('price', float('inf')) <= max_price:
                    agent = self.agents.get(listing['agent_id'], {})
                    matches.append({**listing, 'agent': agent})
        matches.sort(key=lambda x: x.get('price', float('inf')))
        return matches

    def execute_transaction(self, listing_id: str, requester_id: str) -> Dict[str, Any]:
        listing = self.listings.get(listing_id)
        if not listing:
            return {'error': 'Listing not found'}
        transaction = {'listing_id': listing_id, 'requester_id': requester_id, 'provider_id': listing['agent_id'], 'price': listing['price'], 'status': 'completed', 'timestamp': datetime.now().isoformat()}
        self.transactions.append(transaction)
        return transaction
