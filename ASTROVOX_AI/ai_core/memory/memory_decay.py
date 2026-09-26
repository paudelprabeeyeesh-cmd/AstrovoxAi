from typing import List, Dict, Any
import math
from datetime import datetime


class MemoryDecay:
    def __init__(self, decay_rate: float = 0.01, min_importance: float = 0.01):
        self.decay_rate = decay_rate
        self.min_importance = min_importance

    def apply_decay(self, memory: Dict[str, Any], last_accessed: datetime) -> Dict[str, Any]:
        age_seconds = (datetime.now() - last_accessed).total_seconds()
        age_days = age_seconds / 86400.0
        decayed_importance = memory.get('importance', 1.0) * math.exp(-self.decay_rate * age_days)
        memory['importance'] = max(decayed_importance, self.min_importance)
        memory['last_accessed'] = datetime.now().isoformat()
        return memory

    def batch_decay(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        now = datetime.now()
        result = []
        for mem in memories:
            last_accessed = datetime.fromisoformat(mem.get('last_accessed', now.isoformat()))
            result.append(self.apply_decay(mem.copy(), last_accessed))
        return result
