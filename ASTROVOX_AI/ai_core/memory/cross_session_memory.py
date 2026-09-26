from typing import Dict, Any, List
from datetime import datetime
from ASTROVOX_AI.ai_core.memory.memory_decay import MemoryDecay
from ASTROVOX_AI.ai_core.memory.memory_importance_scoring import MemoryImportanceScorer
from ASTROVOX_AI.ai_core.distributed.distributed_cache import DistributedCache


class CrossSessionMemory:
    def __init__(self, cache: DistributedCache, embedding_dim: int = 768, session_ttl: float = 86400.0):
        self.cache = cache
        self.session_ttl = session_ttl
        self.decay = MemoryDecay()
        self.scorer = MemoryImportanceScorer(embedding_dim)
        self.sessions: Dict[str, List[Dict[str, Any]]] = {}

    def store_memory(self, session_id: str, memory: Dict[str, Any]) -> None:
        memory['session_id'] = session_id
        memory['timestamp'] = datetime.now().isoformat()
        memory['importance'] = memory.get('importance', 1.0)
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(memory)
        key = f"memory:{session_id}:{memory.get('id', len(self.sessions[session_id]))}"
        self.cache.set(key, memory, ttl=self.session_ttl)

    def get_session_memories(self, session_id: str) -> List[Dict[str, Any]]:
        memories = self.sessions.get(session_id, [])
        memories = self.decay.batch_decay(memories)
        memories.sort(key=lambda x: x.get('importance', 0), reverse=True)
        return memories

    def get_cross_session_context(self, query_embedding: torch.Tensor, top_k: int = 10) -> List[Dict[str, Any]]:
        all_memories = []
        for session_memories in self.sessions.values():
            all_memories.extend(session_memories)
        if not all_memories:
            return []
        embeddings = torch.stack([torch.tensor(m.get('embedding', [])) for m in all_memories])
        ranked = self.scorer.rank_memories(all_memories, embeddings)
        return [mem for mem, score in ranked[:top_k]]

    def cleanup_expired_sessions(self) -> None:
        now = datetime.now()
        expired = []
        for session_id, memories in self.sessions.items():
            if memories:
                last_mem_time = datetime.fromisoformat(memories[-1].get('timestamp', now.isoformat()))
                if (now - last_mem_time).total_seconds() > self.session_ttl:
                    expired.append(session_id)
        for session_id in expired:
            del self.sessions[session_id]
