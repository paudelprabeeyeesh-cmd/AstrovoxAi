from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class TokenUsageRecord:
    user_id: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class TokenAnalytics:
    def __init__(self):
        self._records: List[TokenUsageRecord] = []
        self._user_records: Dict[str, List[TokenUsageRecord]] = defaultdict(list)
        self._model_stats: Dict[str, Dict[str, float]] = defaultdict(lambda: {
            'total_input': 0, 'total_output': 0, 'total_cost': 0.0, 'count': 0
        })

    def record(self, record: TokenUsageRecord) -> None:
        self._records.append(record)
        self._user_records[record.user_id].append(record)
        model = record.model
        self._model_stats[model]['total_input'] += record.input_tokens
        self._model_stats[model]['total_output'] += record.output_tokens
        self._model_stats[model]['total_cost'] += record.cost
        self._model_stats[model]['count'] += 1
        logger.debug("Token usage recorded: %s tokens for user %s on %s", record.total_tokens, record.user_id, record.model)

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        records = self._user_records.get(user_id, [])
        if not records:
            return {'user_id': user_id, 'total_requests': 0, 'total_tokens': 0, 'total_cost': 0.0}
        total_input = sum(r.input_tokens for r in records)
        total_output = sum(r.output_tokens for r in records)
        total_cost = sum(r.cost for r in records)
        return {
            'user_id': user_id,
            'total_requests': len(records),
            'total_input_tokens': total_input,
            'total_output_tokens': total_output,
            'total_tokens': total_input + total_output,
            'total_cost': round(total_cost, 6),
            'avg_cost_per_request': round(total_cost / len(records), 6),
            'models_used': list({r.model for r in records}),
        }

    def get_model_stats(self, model: str) -> Dict[str, Any]:
        stats = self._model_stats.get(model, {})
        if not stats or stats['count'] == 0:
            return {'model': model, 'total_requests': 0, 'total_tokens': 0, 'total_cost': 0.0}
        return {
            'model': model,
            'total_requests': stats['count'],
            'total_input_tokens': stats['total_input'],
            'total_output_tokens': stats['total_output'],
            'total_tokens': stats['total_input'] + stats['total_output'],
            'total_cost': round(stats['total_cost'], 6),
            'avg_input_per_request': stats['total_input'] // max(stats['count'], 1),
            'avg_output_per_request': stats['total_output'] // max(stats['count'], 1),
            'avg_cost_per_request': round(stats['total_cost'] / max(stats['count'], 1), 6),
        }

    def get_global_stats(self) -> Dict[str, Any]:
        if not self._records:
            return {'total_requests': 0, 'total_tokens': 0, 'total_cost': 0.0, 'unique_users': 0}
        total_input = sum(r.input_tokens for r in self._records)
        total_output = sum(r.output_tokens for r in self._records)
        total_cost = sum(r.cost for r in self._records)
        return {
            'total_requests': len(self._records),
            'total_input_tokens': total_input,
            'total_output_tokens': total_output,
            'total_tokens': total_input + total_output,
            'total_cost': round(total_cost, 6),
            'unique_users': len(self._user_records),
            'unique_models': len(self._model_stats),
        }

    def get_time_series(self, hours: int = 24, bucket_minutes: int = 60) -> List[Dict[str, Any]]:
        cutoff = time.time() - hours * 3600
        recent = [r for r in self._records if r.timestamp >= cutoff]
        buckets: Dict[int, Dict[str, float]] = defaultdict(lambda: {'input': 0.0, 'output': 0.0, 'cost': 0.0, 'count': 0})
        for r in recent:
            bucket_key = int(r.timestamp // (bucket_minutes * 60)) * (bucket_minutes * 60)
            buckets[bucket_key]['input'] += r.input_tokens
            buckets[bucket_key]['output'] += r.output_tokens
            buckets[bucket_key]['cost'] += r.cost
            buckets[bucket_key]['count'] += 1
        return [{'timestamp': k, **v} for k, v in sorted(buckets.items())]

    def get_top_users(self, limit: int = 10, metric: str = 'total_tokens') -> List[Dict[str, Any]]:
        user_metrics = {}
        for user_id, records in self._user_records.items():
            if metric == 'total_tokens':
                value = sum(r.input_tokens + r.output_tokens for r in records)
            elif metric == 'total_cost':
                value = sum(r.cost for r in records)
            else:
                value = len(records)
            user_metrics[user_id] = value
        sorted_users = sorted(user_metrics.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{'user_id': uid, metric: val} for uid, val in sorted_users]
