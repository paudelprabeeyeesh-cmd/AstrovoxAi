"""Analytics dashboard — track application usage and performance."""

import time
import logging
import json
import secrets
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

from .shared import MODEL_COSTS

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class AnalyticsEvent:
    """A single analytics event."""
    event_type: str
    user_id: str
    timestamp: float
    metadata: dict = field(default_factory=dict)


@dataclass
class UsageStats:
    """Aggregated usage statistics."""
    total_requests: int = 0
    total_tokens: int = 0
    total_errors: int = 0
    total_latency: float = 0.0
    average_latency: float = 0.0
    error_rate: float = 0.0
    requests_per_provider: dict = field(default_factory=dict)
    requests_per_model: dict = field(default_factory=dict)
    requests_per_day: dict = field(default_factory=dict)
    active_users: int = 0
    total_users: int = 0


@dataclass
class AIUsageRecord:
    """AI usage record for detailed analytics."""
    user_id: str
    model: str
    provider: str
    tokens: int
    latency: float
    success: bool
    timestamp: float
    workspace_id: str = ""


@dataclass
class TokenUsageRecord:
    """Token usage record for analytics."""
    user_id: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    timestamp: float
    cost: float = 0.0


@dataclass
class CostRecord:
    """Cost record for analytics."""
    user_id: str
    model: str
    provider: str
    amount: float
    input_tokens: int
    output_tokens: int
    timestamp: float


@dataclass
class ModelPerformanceRecord:
    """Model performance record."""
    model: str
    provider: str
    latency: float
    success: bool
    tokens: int
    cost: float
    timestamp: float


@dataclass
class SearchQualityRecord:
    """Search quality record."""
    user_id: str
    query: str
    results_count: int
    clicked: bool
    latency_ms: float
    timestamp: float


@dataclass
class KnowledgeGrowthRecord:
    """Knowledge growth record."""
    documents_indexed: int
    entities_extracted: int
    relationships_created: int
    total_nodes: int
    total_edges: int
    timestamp: float


@dataclass
class WorkflowStatsRecord:
    """Workflow statistics record."""
    workflow_id: str
    workflow_name: str
    status: str
    duration: float
    steps_total: int
    steps_completed: int
    triggered_by: str
    timestamp: float


@dataclass
class AgentPerformanceRecord:
    """Agent performance record."""
    agent_role: str
    agent_name: str
    task_id: str
    task_status: str
    duration: float
    tool_used: str = ""
    timestamp: float


@dataclass
class UserActivityRecord:
    """User activity record."""
    user_id: str
    action: str
    category: str
    session_duration: float
    features_used: list[str]
    timestamp: float


# ============================================================================
# Analytics Tracker
# ============================================================================

class AnalyticsTracker:
    """Track and aggregate application analytics."""

    def __init__(self):
        self._events: list[AnalyticsEvent] = []
        self._user_activity: dict[str, float] = {}
        self._daily_requests: dict[str, int] = defaultdict(int)
        self._provider_requests: dict[str, int] = defaultdict(int)
        self._model_requests: dict[str, int] = defaultdict(int)
        self._error_count: int = 0
        self._total_latency: float = 0.0
        self._total_tokens: int = 0

        self._ai_usage: list[AIUsageRecord] = []
        self._token_usage: list[TokenUsageRecord] = []
        self._cost_records: list[CostRecord] = []
        self._model_performance: list[ModelPerformanceRecord] = []
        self._search_quality: list[SearchQualityRecord] = []
        self._knowledge_growth: list[KnowledgeGrowthRecord] = []
        self._workflow_stats: list[WorkflowStatsRecord] = []
        self._agent_performance: list[AgentPerformanceRecord] = []
        self._user_activity_records: list[UserActivityRecord] = []

        self._session_starts: dict[str, float] = {}

    def track_request(
        self,
        user_id: str,
        model: str,
        provider: str,
        tokens: int = 0,
        latency: float = 0.0,
        success: bool = True,
    ):
        """Track an AI request."""
        now = time.time()
        event = AnalyticsEvent(
            event_type="ai_request",
            user_id=user_id,
            timestamp=now,
            metadata={
                "model": model,
                "provider": provider,
                "tokens": tokens,
                "latency": latency,
                "success": success,
            },
        )
        self._events.append(event)
        self._user_activity[user_id] = now

        day_key = datetime.fromtimestamp(now).strftime("%Y-%m-%d")
        self._daily_requests[day_key] += 1
        self._provider_requests[provider] += 1
        self._model_requests[model] += 1
        self._total_tokens += tokens
        self._total_latency += latency

        if not success:
            self._error_count += 1

        self._ai_usage.append(AIUsageRecord(
            user_id=user_id,
            model=model,
            provider=provider,
            tokens=tokens,
            latency=latency,
            success=success,
            timestamp=now,
        ))

        input_tokens = int(tokens * 0.7)
        output_tokens = tokens - input_tokens
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        self._token_usage.append(TokenUsageRecord(
            user_id=user_id,
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=tokens,
            timestamp=now,
            cost=cost,
        ))
        self._cost_records.append(CostRecord(
            user_id=user_id,
            model=model,
            provider=provider,
            amount=cost,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            timestamp=now,
        ))
        self._model_performance.append(ModelPerformanceRecord(
            model=model,
            provider=provider,
            latency=latency,
            success=success,
            tokens=tokens,
            cost=cost,
            timestamp=now,
        ))

    def track_error(self, user_id: str, error_type: str, details: str = ""):
        """Track an error event."""
        event = AnalyticsEvent(
            event_type="error",
            user_id=user_id,
            timestamp=time.time(),
            metadata={"error_type": error_type, "details": details},
        )
        self._events.append(event)
        self._error_count += 1

    def track_user_action(self, user_id: str, action: str, metadata: dict = None):
        """Track a user action."""
        event = AnalyticsEvent(
            event_type="user_action",
            user_id=user_id,
            timestamp=time.time(),
            metadata=metadata or {},
        )
        self._events.append(event)
        self._user_activity[user_id] = time.time()

    def track_search(self, user_id: str, query: str, results_count: int, clicked: bool, latency_ms: float):
        """Track a search query."""
        now = time.time()
        self._search_quality.append(SearchQualityRecord(
            user_id=user_id,
            query=query[:500],
            results_count=results_count,
            clicked=clicked,
            latency_ms=latency_ms,
            timestamp=now,
        ))

    def track_knowledge_growth(self, documents_indexed: int, entities_extracted: int, relationships_created: int):
        """Track knowledge base growth."""
        now = time.time()
        kg = self._get_knowledge_graph_stats()
        self._knowledge_growth.append(KnowledgeGrowthRecord(
            documents_indexed=documents_indexed,
            entities_extracted=entities_extracted,
            relationships_created=relationships_created,
            total_nodes=kg["total_nodes"],
            total_edges=kg["total_edges"],
            timestamp=now,
        ))

    def track_workflow_execution(
        self,
        workflow_id: str,
        workflow_name: str,
        status: str,
        duration: float,
        steps_total: int,
        steps_completed: int,
        triggered_by: str,
    ):
        """Track workflow execution."""
        now = time.time()
        self._workflow_stats.append(WorkflowStatsRecord(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            status=status,
            duration=duration,
            steps_total=steps_total,
            steps_completed=steps_completed,
            triggered_by=triggered_by,
            timestamp=now,
        ))

    def track_agent_performance(
        self,
        agent_role: str,
        agent_name: str,
        task_id: str,
        task_status: str,
        duration: float,
        tool_used: str = "",
    ):
        """Track agent performance."""
        now = time.time()
        self._agent_performance.append(AgentPerformanceRecord(
            agent_role=agent_role,
            agent_name=agent_name,
            task_id=task_id,
            task_status=task_status,
            duration=duration,
            tool_used=tool_used,
            timestamp=now,
        ))

    def track_user_session(self, user_id: str, action: str, category: str = "general"):
        """Track user session activity."""
        now = time.time()
        if user_id not in self._session_starts:
            self._session_starts[user_id] = now

        session_duration = now - self._session_starts.get(user_id, now)
        features = [action]

        self._user_activity_records.append(UserActivityRecord(
            user_id=user_id,
            action=action,
            category=category,
            session_duration=session_duration,
            features_used=features,
            timestamp=now,
        ))

    def get_usage_stats(self, days: int = 7) -> UsageStats:
        """Get aggregated usage statistics."""
        cutoff = time.time() - (days * 86400)
        recent_events = [e for e in self._events if e.timestamp >= cutoff]

        total_requests = len([e for e in recent_events if e.event_type == "ai_request"])
        error_count = len([e for e in recent_events if e.event_type == "error"])

        total_tokens = sum(
            e.metadata.get("tokens", 0)
            for e in recent_events
            if e.event_type == "ai_request"
        )
        total_latency = sum(
            e.metadata.get("latency", 0.0)
            for e in recent_events
            if e.event_type == "ai_request"
        )

        active_users = len([
            uid for uid, last_seen in self._user_activity.items()
            if last_seen >= cutoff
        ])

        return UsageStats(
            total_requests=total_requests,
            total_tokens=total_tokens,
            total_errors=error_count,
            total_latency=total_latency,
            average_latency=total_latency / total_requests if total_requests > 0 else 0,
            error_rate=error_count / total_requests if total_requests > 0 else 0,
            requests_per_provider=dict(self._provider_requests),
            requests_per_model=dict(self._model_requests),
            requests_per_day=dict(self._daily_requests),
            active_users=active_users,
            total_users=len(self._user_activity),
        )

    def get_ai_usage_analytics(self, days: int = 7) -> dict:
        """Get AI usage analytics."""
        cutoff = time.time() - (days * 86400)
        recent = [r for r in self._ai_usage if r.timestamp >= cutoff]

        by_model: dict[str, int] = defaultdict(int)
        by_provider: dict[str, int] = defaultdict(int)
        by_user: dict[str, int] = defaultdict(int)
        total_success = 0
        total_fail = 0
        total_latency = 0.0

        for r in recent:
            by_model[r.model] += 1
            by_provider[r.provider] += 1
            by_user[r.user_id] += 1
            if r.success:
                total_success += 1
            else:
                total_fail += 1
            total_latency += r.latency

        count = len(recent)
        return {
            "period_days": days,
            "total_requests": count,
            "successful_requests": total_success,
            "failed_requests": total_fail,
            "success_rate": round(total_success / max(count, 1) * 100, 2),
            "average_latency": round(total_latency / max(count, 1), 3),
            "requests_by_model": dict(by_model),
            "requests_by_provider": dict(by_provider),
            "active_users": len(by_user),
            "top_users": sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:10],
        }

    def get_token_analytics(self, days: int = 7) -> dict:
        """Get token usage analytics."""
        cutoff = time.time() - (days * 86400)
        recent = [r for r in self._token_usage if r.timestamp >= cutoff]

        by_user: dict[str, int] = defaultdict(int)
        by_model: dict[str, int] = defaultdict(int)
        by_provider: dict[str, int] = defaultdict(int)

        total_input = 0
        total_output = 0
        total_tokens = 0
        total_cost = 0.0

        for r in recent:
            by_user[r.user_id] += r.total_tokens
            by_model[r.model] += r.total_tokens
            by_provider[r.provider] += r.total_tokens
            total_input += r.input_tokens
            total_output += r.output_tokens
            total_tokens += r.total_tokens
            total_cost += r.cost

        return {
            "period_days": days,
            "total_tokens": total_tokens,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost": round(total_cost, 4),
            "avg_tokens_per_request": round(total_tokens / max(len(recent), 1), 2),
            "tokens_by_user": dict(by_user),
            "tokens_by_model": dict(by_model),
            "tokens_by_provider": dict(by_provider),
            "peak_usage": self._get_peak_token_usage(recent),
        }

    def get_cost_analytics(self, days: int = 7) -> dict:
        """Get cost analytics."""
        cutoff = time.time() - (days * 86400)
        recent = [r for r in self._cost_records if r.timestamp >= cutoff]

        by_user: dict[str, float] = defaultdict(float)
        by_model: dict[str, float] = defaultdict(float)
        by_provider: dict[str, float] = defaultdict(float)

        total_cost = 0.0
        daily_costs: dict[str, float] = defaultdict(float)

        for r in recent:
            by_user[r.user_id] += r.amount
            by_model[r.model] += r.amount
            by_provider[r.provider] += r.amount
            total_cost += r.amount
            day_key = datetime.fromtimestamp(r.timestamp).strftime("%Y-%m-%d")
            daily_costs[day_key] += r.amount

        trend = self._calculate_trend(dict(daily_costs))

        return {
            "period_days": days,
            "total_cost": round(total_cost, 4),
            "cost_by_user": {k: round(v, 4) for k, v in sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:20]},
            "cost_by_model": {k: round(v, 4) for k, v in sorted(by_model.items(), key=lambda x: x[1], reverse=True)},
            "cost_by_provider": {k: round(v, 4) for k, v in sorted(by_provider.items(), key=lambda x: x[1], reverse=True)},
            "daily_costs": {k: round(v, 4) for k, v in sorted(daily_costs.items())},
            "trend": trend,
            "budget_alerts": self._get_budget_alerts(),
        }

    def get_model_performance(self, days: int = 7) -> dict:
        """Get model performance comparison."""
        cutoff = time.time() - (days * 86400)
        recent = [r for r in self._model_performance if r.timestamp >= cutoff]

        by_model: dict[str, dict] = defaultdict(lambda: {
            "count": 0,
            "success": 0,
            "fail": 0,
            "total_latency": 0.0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "latencies": [],
        })

        for r in recent:
            m = by_model[r.model]
            m["count"] += 1
            if r.success:
                m["success"] += 1
            else:
                m["fail"] += 1
            m["total_latency"] += r.latency
            m["total_tokens"] += r.tokens
            m["total_cost"] += r.cost
            m["latencies"].append(r.latency)

        result = {}
        for model, stats in by_model.items():
            latencies = sorted(stats["latencies"])
            count = stats["count"]
            result[model] = {
                "requests": count,
                "success_rate": round(stats["success"] / max(count, 1) * 100, 2),
                "error_rate": round(stats["fail"] / max(count, 1) * 100, 2),
                "avg_latency": round(stats["total_latency"] / max(count, 1), 3),
                "p50_latency": round(latencies[len(latencies) // 2], 3) if latencies else 0,
                "p95_latency": round(latencies[int(len(latencies) * 0.95)], 3) if latencies else 0,
                "p99_latency": round(latencies[int(len(latencies) * 0.99)], 3) if latencies else 0,
                "avg_tokens": round(stats["total_tokens"] / max(count, 1), 2),
                "total_cost": round(stats["total_cost"], 4),
                "quality_score": round(stats["success"] / max(count, 1) * 100, 2),
            }

        return {
            "period_days": days,
            "models": result,
            "best_by_latency": self._get_best_model(result, "avg_latency"),
            "best_by_success": self._get_best_model(result, "success_rate"),
            "best_by_cost": self._get_best_model(result, "avg_tokens"),
        }

    def get_search_analytics(self, days: int = 7) -> dict:
        """Get search quality metrics."""
        cutoff = time.time() - (days * 86400)
        recent = [r for r in self._search_quality if r.timestamp >= cutoff]

        total_queries = len(recent)
        zero_result = len([r for r in recent if r.results_count == 0])
        clicked = len([r for r in recent if r.clicked])
        ctr = (clicked / max(total_queries, 1)) * 100

        query_counts: dict[str, int] = defaultdict(int)
        for r in recent:
            query_counts[r.query] += 1

        top_queries = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        zero_result_queries = list({r.query for r in recent if r.results_count == 0})[:20]

        avg_latency = sum(r.latency_ms for r in recent) / max(total_queries, 1)

        return {
            "period_days": days,
            "total_queries": total_queries,
            "click_through_rate": round(ctr, 2),
            "zero_result_queries": zero_result,
            "zero_result_rate": round(zero_result / max(total_queries, 1) * 100, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "top_queries": top_queries,
            "zero_result_query_list": zero_result_queries,
        }

    def get_knowledge_analytics(self, days: int = 7) -> dict:
        """Get knowledge growth metrics."""
        cutoff = time.time() - (days * 86400)
        recent = [r for r in self._knowledge_growth if r.timestamp >= cutoff]

        total_docs = sum(r.documents_indexed for r in recent)
        total_entities = sum(r.entities_extracted for r in recent)
        total_relationships = sum(r.relationships_created for r in recent)

        latest = recent[-1] if recent else None
        current_nodes = latest.total_nodes if latest else 0
        current_edges = latest.total_edges if latest else 0

        daily_growth: dict[str, dict] = {}
        for r in recent:
            day_key = datetime.fromtimestamp(r.timestamp).strftime("%Y-%m-%d")
            daily_growth[day_key] = {
                "documents": r.documents_indexed,
                "entities": r.entities_extracted,
                "relationships": r.relationships_created,
            }

        return {
            "period_days": days,
            "documents_indexed": total_docs,
            "entities_extracted": total_entities,
            "relationships_created": total_relationships,
            "current_nodes": current_nodes,
            "current_edges": current_edges,
            "knowledge_base_size": current_nodes + current_edges,
            "daily_growth": daily_growth,
        }

    def get_workflow_analytics(self, days: int = 7) -> dict:
        """Get workflow statistics."""
        cutoff = time.time() - (days * 86400)
        recent = [r for r in self._workflow_stats if r.timestamp >= cutoff]

        total = len(recent)
        completed = len([r for r in recent if r.status == "completed"])
        failed = len([r for r in recent if r.status == "failed"])
        cancelled = len([r for r in recent if r.status == "cancelled"])

        total_duration = sum(r.duration for r in recent)
        avg_duration = total_duration / max(total, 1)

        step_completion = sum(r.steps_completed for r in recent)
        total_steps = sum(r.steps_total for r in recent)

        by_workflow: dict[str, int] = defaultdict(int)
        for r in recent:
            by_workflow[r.workflow_name] += 1

        return {
            "period_days": days,
            "total_executions": total,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "success_rate": round(completed / max(total, 1) * 100, 2),
            "avg_duration": round(avg_duration, 3),
            "total_steps_executed": step_completion,
            "total_steps_planned": total_steps,
            "step_completion_rate": round(step_completion / max(total_steps, 1) * 100, 2),
            "top_workflows": sorted(by_workflow.items(), key=lambda x: x[1], reverse=True)[:10],
        }

    def get_agent_analytics(self, days: int = 7) -> dict:
        """Get agent performance metrics."""
        cutoff = time.time() - (days * 86400)
        recent = [r for r in self._agent_performance if r.timestamp >= cutoff]

        total = len(recent)
        completed = len([r for r in recent if r.task_status == "completed"])
        failed = len([r for r in recent if r.task_status == "failed"])

        by_role: dict[str, dict] = defaultdict(lambda: {
            "total": 0,
            "completed": 0,
            "failed": 0,
            "total_duration": 0.0,
            "tools_used": defaultdict(int),
        })

        for r in recent:
            role_stats = by_role[r.agent_role]
            role_stats["total"] += 1
            if r.task_status == "completed":
                role_stats["completed"] += 1
            elif r.task_status == "failed":
                role_stats["failed"] += 1
            role_stats["total_duration"] += r.duration
            if r.tool_used:
                role_stats["tools_used"][r.tool_used] += 1

        agents = {}
        for role, stats in by_role.items():
            agents[role] = {
                "total_tasks": stats["total"],
                "completed": stats["completed"],
                "failed": stats["failed"],
                "success_rate": round(stats["completed"] / max(stats["total"], 1) * 100, 2),
                "avg_duration": round(stats["total_duration"] / max(stats["total"], 1), 3),
                "top_tools": dict(sorted(stats["tools_used"].items(), key=lambda x: x[1], reverse=True)[:5]),
            }

        return {
            "period_days": days,
            "total_tasks": total,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "success_rate": round(completed / max(total, 1) * 100, 2),
            "agents": agents,
        }

    def get_user_analytics(self, days: int = 7) -> dict:
        """Get user activity metrics."""
        cutoff = time.time() - (days * 86400)
        recent = [r for r in self._user_activity_records if r.timestamp >= cutoff]

        active_users = len({
            r.user_id for r in recent
        })

        by_user: dict[str, dict] = defaultdict(lambda: {
            "actions": 0,
            "categories": defaultdict(int),
            "total_duration": 0.0,
            "features": defaultdict(int),
        })

        for r in recent:
            user_stats = by_user[r.user_id]
            user_stats["actions"] += 1
            user_stats["categories"][r.category] += 1
            user_stats["total_duration"] += r.session_duration
            for f in r.features_used:
                user_stats["features"][f] += 1

        top_users = []
        for user_id, stats in by_user.items():
            top_users.append({
                "user_id": user_id,
                "actions": stats["actions"],
                "top_category": max(stats["categories"].items(), key=lambda x: x[1])[0] if stats["categories"] else "",
                "avg_session_duration": round(stats["total_duration"] / max(stats["actions"], 1), 2),
                "top_features": sorted(stats["features"].items(), key=lambda x: x[1], reverse=True)[:5],
            })
        top_users.sort(key=lambda x: x["actions"], reverse=True)

        return {
            "period_days": days,
            "active_users": active_users,
            "total_actions": len(recent),
            "top_users": top_users[:20],
            "engagement_by_category": dict(
                sorted(
                    ((c, sum(u["categories"].get(c, 0) for u in by_user.values()))
                     for c in {c for u in by_user.values() for c in u["categories"]}),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            ),
        }

    def get_overview(self, days: int = 7) -> dict:
        """Get platform-wide analytics overview."""
        usage = self.get_usage_stats(days=days)
        ai = self.get_ai_usage_analytics(days=days)
        tokens = self.get_token_analytics(days=days)
        costs = self.get_cost_analytics(days=days)
        models = self.get_model_performance(days=days)
        search = self.get_search_analytics(days=days)
        knowledge = self.get_knowledge_analytics(days=days)
        workflows = self.get_workflow_analytics(days=days)
        agents = self.get_agent_analytics(days=days)
        users = self.get_user_analytics(days=days)

        return {
            "period_days": days,
            "usage": {
                "total_requests": usage.total_requests,
                "total_tokens": usage.total_tokens,
                "active_users": usage.active_users,
                "avg_latency": round(usage.average_latency, 3),
                "error_rate": round(usage.error_rate, 4),
            },
            "ai_usage": {
                "total_requests": ai["total_requests"],
                "success_rate": ai["success_rate"],
                "avg_latency": ai["average_latency"],
            },
            "tokens": {
                "total_tokens": tokens["total_tokens"],
                "total_cost": tokens["total_cost"],
                "peak_usage": tokens["peak_usage"],
            },
            "costs": {
                "total_cost": costs["total_cost"],
                "trend": costs["trend"],
            },
            "models": {
                "model_count": len(models["models"]),
                "best_by_latency": models["best_by_latency"],
                "best_by_success": models["best_by_success"],
            },
            "search": {
                "total_queries": search["total_queries"],
                "ctr": search["click_through_rate"],
                "zero_result_rate": search["zero_result_rate"],
            },
            "knowledge": {
                "documents_indexed": knowledge["documents_indexed"],
                "entities_extracted": knowledge["entities_extracted"],
                "kb_size": knowledge["knowledge_base_size"],
            },
            "workflows": {
                "total_executions": workflows["total_executions"],
                "success_rate": workflows["success_rate"],
            },
            "agents": {
                "total_tasks": agents["total_tasks"],
                "success_rate": agents["success_rate"],
            },
            "users": {
                "active_users": users["active_users"],
                "total_actions": users["total_actions"],
            },
        }

    def get_provider_breakdown(self) -> dict:
        """Get usage breakdown by provider."""
        return dict(self._provider_requests)

    def get_model_breakdown(self) -> dict:
        """Get usage breakdown by model."""
        return dict(self._model_requests)

    def get_daily_usage(self, days: int = 30) -> dict:
        """Get daily request counts."""
        result = {}
        today = datetime.now()
        for i in range(days):
            day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            result[day] = self._daily_requests.get(day, 0)
        return result

    def get_cost_estimate(self) -> dict:
        """Estimate costs based on usage."""
        costs = {}
        for model, count in self._model_requests.items():
            if model in MODEL_COSTS:
                cost = MODEL_COSTS[model]
                estimated = (cost["input"] + cost["output"]) * count
                costs[model] = round(estimated, 4)
        return costs

    def get_dashboard_data(self) -> dict:
        """Get all dashboard data."""
        stats = self.get_usage_stats()
        return {
            "total_requests": stats.total_requests,
            "total_tokens": stats.total_tokens,
            "average_latency": round(stats.average_latency, 3),
            "error_rate": round(stats.error_rate, 4),
            "active_users": stats.active_users,
            "total_users": stats.total_users,
            "provider_breakdown": self.get_provider_breakdown(),
            "model_breakdown": self.get_model_breakdown(),
            "daily_usage": self.get_daily_usage(),
            "cost_estimate": self.get_cost_estimate(),
        }

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for a request."""
        costs = MODEL_COSTS.get(model, {"input": 0, "output": 0})
        input_cost = costs["input"] * input_tokens / 1000
        output_cost = costs["output"] * output_tokens / 1000
        return round(input_cost + output_cost, 6)

    def export_analytics(self, days: int = 30, format: str = "json") -> dict:
        """Export analytics data."""
        cutoff = time.time() - (days * 86400)
        events = [e for e in self._events if e.timestamp >= cutoff]

        export_data = {
            "exported_at": datetime.now().isoformat(),
            "period_days": days,
            "overview": self.get_overview(days=days),
            "ai_usage": [
                {
                    "user_id": r.user_id,
                    "model": r.model,
                    "provider": r.provider,
                    "tokens": r.tokens,
                    "latency": r.latency,
                    "success": r.success,
                    "timestamp": datetime.fromtimestamp(r.timestamp).isoformat(),
                }
                for r in self._ai_usage if r.timestamp >= cutoff
            ],
            "token_usage": [
                {
                    "user_id": r.user_id,
                    "model": r.model,
                    "provider": r.provider,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "total_tokens": r.total_tokens,
                    "cost": r.cost,
                    "timestamp": datetime.fromtimestamp(r.timestamp).isoformat(),
                }
                for r in self._token_usage if r.timestamp >= cutoff
            ],
            "search_quality": [
                {
                    "user_id": r.user_id,
                    "query": r.query,
                    "results_count": r.results_count,
                    "clicked": r.clicked,
                    "latency_ms": r.latency_ms,
                    "timestamp": datetime.fromtimestamp(r.timestamp).isoformat(),
                }
                for r in self._search_quality if r.timestamp >= cutoff
            ],
            "workflows": [
                {
                    "workflow_id": r.workflow_id,
                    "workflow_name": r.workflow_name,
                    "status": r.status,
                    "duration": r.duration,
                    "steps_total": r.steps_total,
                    "steps_completed": r.steps_completed,
                    "timestamp": datetime.fromtimestamp(r.timestamp).isoformat(),
                }
                for r in self._workflow_stats if r.timestamp >= cutoff
            ],
        }

        return export_data

    async def persist_to_supabase(self, table_name: str = "analytics_events"):
        """Persist analytics events to Supabase."""
        try:
            import secrets
            from .supabase_client import get_supabase
            supabase = get_supabase()

            events_to_insert = []
            for e in self._events[-500:]:
                events_to_insert.append({
                    "id": secrets.token_hex(8),
                    "event_type": e.event_type,
                    "user_id": e.user_id,
                    "timestamp": datetime.fromtimestamp(e.timestamp).isoformat(),
                    "metadata": json.dumps(e.metadata),
                })

            if events_to_insert:
                supabase.table(table_name).insert(events_to_insert).execute()
                logger.info(f"Persisted {len(events_to_insert)} analytics events to Supabase")
        except Exception as e:
            logger.error(f"Failed to persist analytics to Supabase: {str(e)}")

    def _get_knowledge_graph_stats(self) -> dict:
        """Get knowledge graph stats from the knowledge system."""
        try:
            from .knowledge_system import knowledge_system
            return knowledge_system.get_stats()
        except Exception:
            return {"total_nodes": 0, "total_edges": 0}

    def _get_peak_token_usage(self, records: list) -> dict:
        """Calculate peak token usage."""
        if not records:
            return {"day": 0, "hour": 0}
        daily: dict[str, int] = defaultdict(int)
        hourly: dict[int, int] = defaultdict(int)
        for r in records:
            day_key = datetime.fromtimestamp(r.timestamp).strftime("%Y-%m-%d")
            daily[day_key] += r.total_tokens
            hourly[datetime.fromtimestamp(r.timestamp).hour] += r.total_tokens
        peak_day = max(daily.items(), key=lambda x: x[1]) if daily else ("", 0)
        peak_hour = max(hourly.items(), key=lambda x: x[1]) if hourly else (0, 0)
        return {"day": peak_day[1], "day_date": peak_day[0], "hour": peak_hour[1], "hour_of_day": peak_hour[0]}

    def _calculate_trend(self, daily_values: dict[str, float]) -> str:
        """Calculate cost trend."""
        if len(daily_values) < 2:
            return "stable"
        values = list(daily_values.values())
        recent = sum(values[-3:]) / min(3, len(values[-3:]))
        older = sum(values[:3]) / min(3, len(values[:3]))
        if recent > older * 1.1:
            return "increasing"
        elif recent < older * 0.9:
            return "decreasing"
        return "stable"

    def _get_budget_alerts(self) -> list[dict]:
        """Get budget alerts from cost tracker."""
        alerts = []
        try:
            from .cost_management import cost_tracker
            for budget_id, budget in cost_tracker._budgets.items():
                for user_id in list(cost_tracker._user_usage.keys())[:10]:
                    check = cost_tracker.check_budget(budget_id, user_id)
                    if check.get("exceeded"):
                        alerts.append({
                            "budget_id": budget_id,
                            "budget_name": budget.name,
                            "user_id": user_id,
                            "percentage": check["percentage"],
                            "remaining": check["remaining"],
                        })
        except Exception:
            pass
        return alerts[:20]

    def _get_best_model(self, models: dict, metric: str) -> str | None:
        """Get the best model by a given metric."""
        if not models:
            return None
        if metric in ("avg_latency", "avg_tokens"):
            return min(models.items(), key=lambda x: x[1].get(metric, float("inf")))[0]
        return max(models.items(), key=lambda x: x[1].get(metric, 0))[0]


# Singleton instance
analytics = AnalyticsTracker()
