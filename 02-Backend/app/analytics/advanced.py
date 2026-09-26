"""Advanced analytics engine with 15 high-value analytics capabilities."""

from __future__ import annotations

import json
import math
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field

from .shared import MODEL_COSTS
from app.repositories.database.client import get_db


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class AnalyticsEvent:
    event_type: str
    user_id: str
    timestamp: float
    metadata: dict = field(default_factory=dict)
    session_id: str = ""
    device_type: str = ""
    page_url: str = ""
    duration_ms: int = 0


@dataclass
class BehaviorEvent:
    user_id: str
    session_id: str
    event_type: str
    page_url: str
    element_id: str = ""
    element_class: str = ""
    properties: dict = field(default_factory=dict)
    time_on_page_seconds: int = 0
    scroll_depth_percent: int = 0
    timestamp: float = 0.0


@dataclass
class FeatureAdoptionRecord:
    user_id: str
    feature_name: str
    feature_category: str
    first_used_at: float
    last_used_at: float
    usage_count: int = 1
    is_adopted: bool = False
    adoption_date: Optional[float] = None
    time_to_adoption_seconds: Optional[int] = None


@dataclass
class ABTestRecord:
    test_id: str
    test_name: str
    description: str
    variant_a: dict
    variant_b: dict
    status: str
    metric_name: str
    start_date: Optional[float]
    end_date: Optional[float]
    min_sample_size: int = 100
    confidence_level: float = 0.95
    created_by: str = ""


@dataclass
class ABTestAssignment:
    test_id: str
    user_id: str
    variant: str
    assigned_at: float


@dataclass
class ABTestEvent:
    test_id: str
    user_id: str
    variant: str
    event_name: str
    event_value: Optional[float]
    properties: dict = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass
class FunnelRecord:
    funnel_id: str
    funnel_name: str
    description: str
    steps: list[dict]
    is_active: bool = True


@dataclass
class FunnelEvent:
    funnel_id: str
    user_id: str
    session_id: str
    step_index: int
    step_name: str
    entered_at: float
    exited_at: Optional[float] = None
    completed: bool = False
    drop_off_reason: str = ""
    properties: dict = field(default_factory=dict)


@dataclass
class CohortRecord:
    cohort_id: str
    cohort_name: str
    description: str
    definition: dict
    member_count: int = 0
    created_by: str = ""


@dataclass
class CohortMember:
    cohort_id: str
    user_id: str
    joined_at: float
    left_at: Optional[float] = None
    is_active: bool = True


@dataclass
class CohortMetric:
    cohort_id: str
    date: str
    active_users: int = 0
    new_retained: int = 0
    returning_users: int = 0
    churned_users: int = 0
    retention_rate: float = 0.0
    revenue: float = 0.0


@dataclass
class RetentionSnapshot:
    user_id: str
    cohort_date: str
    day_0: bool = True
    day_1: bool = False
    day_3: bool = False
    day_7: bool = False
    day_14: bool = False
    day_30: bool = False
    day_60: bool = False
    day_90: bool = False
    last_active_date: Optional[str] = None


@dataclass
class RevenueEvent:
    user_id: str
    event_type: str
    amount: float
    currency: str = "USD"
    plan_name: str = ""
    plan_interval: str = ""
    payment_method: str = ""
    stripe_invoice_id: str = ""
    stripe_customer_id: str = ""
    metadata: dict = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass
class CustomReport:
    report_id: str
    report_name: str
    description: str
    created_by: str
    config: dict
    schedule: str = ""
    recipients: list[str] = field(default_factory=list)
    last_run_at: Optional[float] = None
    is_public: bool = False


@dataclass
class ConversationRecord:
    conversation_id: str
    user_id: str
    model: str
    provider: str
    message_count: int
    total_tokens: int
    total_cost: float
    duration_seconds: float
    started_at: float
    ended_at: float
    sentiment: str = "neutral"
    satisfaction_score: Optional[float] = None


@dataclass
class GPUMetric:
    device_id: int
    utilization_percent: float
    memory_used_mb: float
    memory_total_mb: float
    temperature_c: float
    timestamp: float = 0.0


@dataclass
class MemoryMetric:
    total_mb: float
    used_mb: float
    available_mb: float
    percent: float
    swap_used_mb: float = 0.0
    timestamp: float = 0.0


@dataclass
class APIMetric:
    endpoint: str
    method: str
    status_code: int
    latency_ms: float
    user_id: str = ""
    model: str = ""
    provider: str = ""
    tokens: int = 0
    timestamp: float = 0.0


# ============================================================================
# Advanced Analytics Engine
# ============================================================================

class AdvancedAnalyticsEngine:
    """Comprehensive analytics engine with 15 high-value features."""

    def __init__(self):
        self._events: list[AnalyticsEvent] = []
        self._behavior_events: list[BehaviorEvent] = []
        self._feature_adoption: dict[str, FeatureAdoptionRecord] = {}
        self._ab_tests: dict[str, ABTestRecord] = {}
        self._ab_assignments: dict[str, ABTestAssignment] = {}
        self._ab_events: list[ABTestEvent] = []
        self._funnels: dict[str, FunnelRecord] = {}
        self._funnel_events: list[FunnelEvent] = []
        self._cohorts: dict[str, CohortRecord] = {}
        self._cohort_members: list[CohortMember] = []
        self._cohort_metrics: list[CohortMetric] = []
        self._retention_snapshots: dict[str, RetentionSnapshot] = {}
        self._revenue_events: list[RevenueEvent] = []
        self._custom_reports: dict[str, CustomReport] = {}
        self._conversations: list[ConversationRecord] = []
        self._sessions: dict[str, dict] = {}
        self._gpu_metrics: list[GPUMetric] = []
        self._memory_metrics: list[MemoryMetric] = []
        self._api_metrics: list[APIMetric] = []

        # Feature definitions for adoption tracking
        self._known_features = {
            "chat": "Core",
            "memory": "Core",
            "search": "Core",
            "voice_input": "Advanced",
            "image_gen": "Advanced",
            "code_execution": "Advanced",
            "rag": "Advanced",
            "agents": "Advanced",
            "workflows": "Enterprise",
            "collaboration": "Enterprise",
            "api_access": "Enterprise",
            "custom_models": "Enterprise",
        }
        self._load_from_db()

    def _persist_gpu_metric(self, metric: "GPUMetric") -> None:
        try:
            event_id = str(uuid.uuid4())
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO gpu_metrics (id, device_id, utilization_percent, memory_used_mb, memory_total_mb, temperature_c, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        event_id,
                        metric.device_id,
                        metric.utilization_percent,
                        metric.memory_used_mb,
                        metric.memory_total_mb,
                        metric.temperature_c,
                        datetime.fromtimestamp(metric.timestamp, tz=timezone.utc).isoformat() if metric.timestamp else datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()
        except Exception:
            pass

    def _persist_memory_metric(self, metric: "MemoryMetric") -> None:
        try:
            event_id = str(uuid.uuid4())
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO memory_metrics (id, total_mb, used_mb, available_mb, percent, swap_used_mb, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        event_id,
                        metric.total_mb,
                        metric.used_mb,
                        metric.available_mb,
                        metric.percent,
                        metric.swap_used_mb,
                        datetime.fromtimestamp(metric.timestamp, tz=timezone.utc).isoformat() if metric.timestamp else datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()
        except Exception:
            pass

    def _persist_api_metric(self, metric: "APIMetric") -> None:
        try:
            event_id = str(uuid.uuid4())
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO api_metrics (id, endpoint, method, status_code, latency_ms, user_id, model, provider, tokens, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        event_id,
                        metric.endpoint,
                        metric.method,
                        metric.status_code,
                        metric.latency_ms,
                        metric.user_id,
                        metric.model,
                        metric.provider,
                        metric.tokens,
                        datetime.fromtimestamp(metric.timestamp, tz=timezone.utc).isoformat() if metric.timestamp else datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()
        except Exception:
            pass

    def _load_gpu_metrics_from_db(self) -> None:
        try:
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT device_id, utilization_percent, memory_used_mb, memory_total_mb, temperature_c, created_at FROM gpu_metrics ORDER BY created_at ASC"
                ).fetchall()
                for r in rows:
                    try:
                        ts = datetime.fromisoformat(r["created_at"]).timestamp()
                    except Exception:
                        ts = time.time()
                    self._gpu_metrics.append(GPUMetric(
                        device_id=r["device_id"],
                        utilization_percent=r["utilization_percent"],
                        memory_used_mb=r["memory_used_mb"],
                        memory_total_mb=r["memory_total_mb"],
                        temperature_c=r["temperature_c"],
                        timestamp=ts,
                    ))
        except Exception:
            pass

    def _load_memory_metrics_from_db(self) -> None:
        try:
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT total_mb, used_mb, available_mb, percent, swap_used_mb, created_at FROM memory_metrics ORDER BY created_at ASC"
                ).fetchall()
                for r in rows:
                    try:
                        ts = datetime.fromisoformat(r["created_at"]).timestamp()
                    except Exception:
                        ts = time.time()
                    self._memory_metrics.append(MemoryMetric(
                        total_mb=r["total_mb"],
                        used_mb=r["used_mb"],
                        available_mb=r["available_mb"],
                        percent=r["percent"],
                        swap_used_mb=r["swap_used_mb"],
                        timestamp=ts,
                    ))
        except Exception:
            pass

    def _load_api_metrics_from_db(self) -> None:
        try:
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT endpoint, method, status_code, latency_ms, user_id, model, provider, tokens, created_at FROM api_metrics ORDER BY created_at ASC"
                ).fetchall()
                for r in rows:
                    try:
                        ts = datetime.fromisoformat(r["created_at"]).timestamp()
                    except Exception:
                        ts = time.time()
                    self._api_metrics.append(APIMetric(
                        endpoint=r["endpoint"],
                        method=r["method"],
                        status_code=r["status_code"],
                        latency_ms=r["latency_ms"],
                        user_id=r["user_id"],
                        model=r["model"],
                        provider=r["provider"],
                        tokens=r["tokens"],
                        timestamp=ts,
                    ))
        except Exception:
            pass

    def _load_from_db(self) -> None:
        try:
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT id, event_type, properties, created_at FROM analytics_events"
                ).fetchall()
                for r in rows:
                    try:
                        props = json.loads(r["properties"])
                    except Exception:
                        props = {}
                    self._events.append(AnalyticsEvent(
                        event_type=r["event_type"],
                        user_id=props.get("user_id", ""),
                        timestamp=datetime.fromisoformat(r["created_at"]).timestamp() if r["created_at"] else time.time(),
                        metadata=props,
                    ))
        except Exception:
            pass
        self._load_gpu_metrics_from_db()
        self._load_memory_metrics_from_db()
        self._load_api_metrics_from_db()

    def _persist_event(self, event_type: str, user_id: str, metadata: dict) -> None:
        try:
            event_id = str(uuid.uuid4())
            payload = json.dumps(metadata or {})
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO analytics_events (id, event_type, properties, created_at) VALUES (?, ?, ?, ?)",
                    (event_id, event_type, payload, datetime.now(timezone.utc).isoformat()),
                )
                conn.commit()
        except Exception:
            pass

    def _persist_ab_event(self, event: "ABTestEvent") -> None:
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO ab_events (id, test_id, user_id, variant, event_name, event_value, properties, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid.uuid4()),
                        event.test_id,
                        event.user_id,
                        event.variant,
                        event.event_name,
                        event.event_value,
                        json.dumps(event.properties or {}),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()
        except Exception:
            pass

    def _persist_funnel_event(self, event: "FunnelEvent") -> None:
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO funnel_events (id, funnel_id, user_id, session_id, step_index, step_name, entered_at, exited_at, completed, drop_off_reason, properties) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid.uuid4()),
                        event.funnel_id,
                        event.user_id,
                        event.session_id,
                        event.step_index,
                        event.step_name,
                        datetime.fromtimestamp(event.entered_at, tz=timezone.utc).isoformat() if event.entered_at else None,
                        datetime.fromtimestamp(event.exited_at, tz=timezone.utc).isoformat() if event.exited_at else None,
                        1 if event.completed else 0,
                        event.drop_off_reason,
                        json.dumps(event.properties or {}),
                    ),
                )
                conn.commit()
        except Exception:
            pass

    def _persist_cohort_member(self, member: "CohortMember") -> None:
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO cohort_members (id, cohort_id, user_id, joined_at, left_at, is_active) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid.uuid4()),
                        member.cohort_id,
                        member.user_id,
                        datetime.fromtimestamp(member.joined_at, tz=timezone.utc).isoformat() if member.joined_at else datetime.now(timezone.utc).isoformat(),
                        datetime.fromtimestamp(member.left_at, tz=timezone.utc).isoformat() if member.left_at else None,
                        1 if member.is_active else 0,
                    ),
                )
                conn.commit()
        except Exception:
            pass

    def _persist_retention_snapshot(self, snapshot: "RetentionSnapshot") -> None:
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO retention_snapshots (id, user_id, cohort_date, day_0, day_1, day_3, day_7, day_14, day_30, day_60, day_90, last_active_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid.uuid4()),
                        snapshot.user_id,
                        snapshot.cohort_date,
                        1 if snapshot.day_0 else 0,
                        1 if snapshot.day_1 else 0,
                        1 if snapshot.day_3 else 0,
                        1 if snapshot.day_7 else 0,
                        1 if snapshot.day_14 else 0,
                        1 if snapshot.day_30 else 0,
                        1 if snapshot.day_60 else 0,
                        1 if snapshot.day_90 else 0,
                        snapshot.last_active_date,
                    ),
                )
                conn.commit()
        except Exception:
            pass

    def _persist_revenue_event(self, event: "RevenueEvent") -> None:
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO revenue_events (id, user_id, event_type, amount, currency, plan_name, plan_interval, payment_method, stripe_invoice_id, stripe_customer_id, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid.uuid4()),
                        event.user_id,
                        event.event_type,
                        event.amount,
                        event.currency,
                        event.plan_name,
                        event.plan_interval,
                        event.payment_method,
                        event.stripe_invoice_id,
                        event.stripe_customer_id,
                        json.dumps(event.metadata or {}),
                        datetime.fromtimestamp(event.timestamp, tz=timezone.utc).isoformat() if event.timestamp else datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()
        except Exception:
            pass

    def _persist_custom_report(self, report: "CustomReport") -> None:
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO custom_reports (id, report_name, description, created_by, config, schedule, recipients, last_run_at, is_public, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        report.report_id,
                        report.report_name,
                        report.description,
                        report.created_by,
                        json.dumps(report.config or {}),
                        report.schedule,
                        json.dumps(report.recipients or []),
                        datetime.fromtimestamp(report.last_run_at, tz=timezone.utc).isoformat() if report.last_run_at else None,
                        1 if report.is_public else 0,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()
        except Exception:
            pass

    def _persist_conversation(self, conv: "ConversationRecord") -> None:
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO analytics_events (id, event_type, properties, created_at) VALUES (?, ?, ?, ?)",
                    (
                        conv.conversation_id,
                        "conversation",
                        json.dumps({
                            "user_id": conv.user_id,
                            "model": conv.model,
                            "provider": conv.provider,
                            "message_count": conv.message_count,
                            "total_tokens": conv.total_tokens,
                            "total_cost": conv.total_cost,
                            "sentiment": conv.sentiment,
                            "satisfaction_score": conv.satisfaction_score,
                        }),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 1. Real-time Analytics Dashboard
    # ------------------------------------------------------------------
    def get_realtime_dashboard(self, days: int = 1) -> dict:
        now = time.time()
        cutoff = now - (days * 86400)

        recent_events = [e for e in self._events if e.timestamp >= cutoff]
        recent_behavior = [e for e in self._behavior_events if e.timestamp >= cutoff]
        recent_revenue = [e for e in self._revenue_events if e.timestamp >= cutoff]

        active_sessions = len(self._sessions)
        active_users = len({e.user_id for e in recent_events})

        events_per_minute = self._calculate_rate(recent_events, 60)
        requests_per_minute = len([e for e in recent_events if e.event_type == "ai_request"]) / max(days * 1440, 1)

        revenue_today = sum(e.amount for e in recent_revenue if e.timestamp >= now - 86400)

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period_days": days,
            "active_users": active_users,
            "active_sessions": active_sessions,
            "total_events": len(recent_events),
            "events_per_minute": round(events_per_minute, 2),
            "requests_per_minute": round(requests_per_minute, 4),
            "behavior_events": len(recent_behavior),
            "revenue_today": round(revenue_today, 4),
            "top_pages": self._get_top_pages(recent_behavior),
            "top_features": self._get_top_features(recent_events),
        }

    def _calculate_rate(self, events: list, window_seconds: int) -> float:
        if not events:
            return 0.0
        time_span = max(events[-1].timestamp - events[0].timestamp, window_seconds)
        return len(events) / (time_span / window_seconds)

    def _get_top_pages(self, behavior_events: list) -> list[tuple[str, int]]:
        page_counts: dict[str, int] = defaultdict(int)
        for e in behavior_events:
            if e.page_url:
                page_counts[e.page_url] += 1
        return sorted(page_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    def _get_top_features(self, events: list) -> list[tuple[str, int]]:
        feature_counts: dict[str, int] = defaultdict(int)
        for e in events:
            if e.event_type == "feature_used":
                feature = e.metadata.get("feature_name", "unknown")
                feature_counts[feature] += 1
        return sorted(feature_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # ------------------------------------------------------------------
    # 2. User Behavior Analytics
    # ------------------------------------------------------------------
    def track_behavior(self, event: BehaviorEvent):
        self._behavior_events.append(event)

    def get_user_behavior_analytics(self, days: int = 7, user_id: Optional[str] = None) -> dict:
        cutoff = time.time() - (days * 86400)
        events = [e for e in self._behavior_events if e.timestamp >= cutoff]
        if user_id:
            events = [e for e in events if e.user_id == user_id]

        event_type_counts: dict[str, int] = defaultdict(int)
        page_views: dict[str, int] = defaultdict(int)
        avg_time_on_page: dict[str, list[int]] = defaultdict(list)
        avg_scroll_depth: dict[str, list[int]] = defaultdict(list)
        session_durations: dict[str, list[float]] = defaultdict(list)

        for e in events:
            event_type_counts[e.event_type] += 1
            if e.page_url:
                page_views[e.page_url] += 1
                if e.time_on_page_seconds > 0:
                    avg_time_on_page[e.page_url].append(e.time_on_page_seconds)
                if e.scroll_depth_percent > 0:
                    avg_scroll_depth[e.page_url].append(e.scroll_depth_percent)

        top_pages = sorted(page_views.items(), key=lambda x: x[1], reverse=True)[:20]

        return {
            "period_days": days,
            "total_behavior_events": len(events),
            "unique_users": len({e.user_id for e in events}),
            "event_type_breakdown": dict(event_type_counts),
            "top_pages": [{"page": p, "views": v} for p, v in top_pages],
            "avg_time_on_page": {
                p: round(sum(times) / len(times), 1) for p, times in list(avg_time_on_page.items())[:10]
            },
            "avg_scroll_depth": {
                p: round(sum(depths) / len(depths), 1) for p, depths in list(avg_scroll_depth.items())[:10]
            },
            "click_heatmap": self._get_click_heatmap(events),
        }

    def _get_click_heatmap(self, events: list) -> dict:
        clicks = [e for e in events if e.event_type in ("click", "tap")]
        element_clicks: dict[str, int] = defaultdict(int)
        for e in clicks:
            key = e.element_class or e.element_id or "unknown"
            element_clicks[key] += 1
        return dict(sorted(element_clicks.items(), key=lambda x: x[1], reverse=True)[:20])

    # ------------------------------------------------------------------
    # 3. Token Usage Analytics
    # ------------------------------------------------------------------
    def get_token_analytics(self, days: int = 7, user_id: Optional[str] = None) -> dict:
        cutoff = time.time() - (days * 86400)
        events = [e for e in self._events if e.timestamp >= cutoff and e.event_type == "ai_request"]
        if user_id:
            events = [e for e in events if e.user_id == user_id]

        by_user: dict[str, int] = defaultdict(int)
        by_model: dict[str, int] = defaultdict(int)
        by_provider: dict[str, int] = defaultdict(int)
        by_hour: dict[int, int] = defaultdict(int)
        by_day: dict[str, int] = defaultdict(int)

        total_input = 0
        total_output = 0
        total_tokens = 0
        total_cost = 0.0

        for e in events:
            tokens = e.metadata.get("tokens", 0)
            model = e.metadata.get("model", "unknown")
            provider = e.metadata.get("provider", "unknown")
            input_tokens = int(tokens * 0.7)
            output_tokens = tokens - input_tokens
            cost = MODEL_COSTS.get(model, {"input": 0, "output": 0})
            event_cost = (cost["input"] * input_tokens + cost["output"] * output_tokens) / 1000

            by_user[e.user_id] += tokens
            by_model[model] += tokens
            by_provider[provider] += tokens
            total_input += input_tokens
            total_output += output_tokens
            total_tokens += tokens
            total_cost += event_cost

            dt = datetime.fromtimestamp(e.timestamp)
            by_hour[dt.hour] += tokens
            by_day[dt.strftime("%Y-%m-%d")] += tokens

        return {
            "period_days": days,
            "total_tokens": total_tokens,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost": round(total_cost, 4),
            "avg_tokens_per_request": round(total_tokens / max(len(events), 1), 2),
            "tokens_by_user": dict(sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:20]),
            "tokens_by_model": dict(sorted(by_model.items(), key=lambda x: x[1], reverse=True)),
            "tokens_by_provider": dict(sorted(by_provider.items(), key=lambda x: x[1], reverse=True)),
            "tokens_by_hour": dict(sorted(by_hour.items())),
            "tokens_by_day": dict(sorted(by_day.items())),
            "peak_hour": max(by_hour.items(), key=lambda x: x[1]) if by_hour else (0, 0),
            "peak_day": max(by_day.items(), key=lambda x: x[1]) if by_day else ("", 0),
        }

    # ------------------------------------------------------------------
    # 4. Cost Analytics and Billing Insights
    # ------------------------------------------------------------------
    def get_cost_analytics(self, days: int = 7, user_id: Optional[str] = None) -> dict:
        cutoff = time.time() - (days * 86400)
        events = [e for e in self._events if e.timestamp >= cutoff and e.event_type == "ai_request"]
        revenue = [e for e in self._revenue_events if e.timestamp >= cutoff]
        if user_id:
            events = [e for e in events if e.user_id == user_id]
            revenue = [e for e in revenue if e.user_id == user_id]

        by_user: dict[str, float] = defaultdict(float)
        by_model: dict[str, float] = defaultdict(float)
        by_provider: dict[str, float] = defaultdict(float)
        daily_costs: dict[str, float] = defaultdict(float)

        total_cost = 0.0
        for e in events:
            tokens = e.metadata.get("tokens", 0)
            model = e.metadata.get("model", "unknown")
            provider = e.metadata.get("provider", "unknown")
            input_tokens = int(tokens * 0.7)
            output_tokens = tokens - input_tokens
            costs = MODEL_COSTS.get(model, {"input": 0, "output": 0})
            cost = (costs["input"] * input_tokens + costs["output"] * output_tokens) / 1000

            by_user[e.user_id] += cost
            by_model[model] += cost
            by_provider[provider] += cost
            total_cost += cost
            day_key = datetime.fromtimestamp(e.timestamp).strftime("%Y-%m-%d")
            daily_costs[day_key] += cost

        # Revenue metrics
        total_revenue = sum(r.amount for r in revenue)
        mrr = self._calculate_mrr(revenue)
        arr = mrr * 12

        trend = self._calculate_trend(dict(daily_costs))

        return {
            "period_days": days,
            "total_api_cost": round(total_cost, 4),
            "total_revenue": round(total_revenue, 4),
            "net_margin": round(total_revenue - total_cost, 4),
            "cost_by_user": {k: round(v, 4) for k, v in sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:20]},
            "cost_by_model": {k: round(v, 4) for k, v in sorted(by_model.items(), key=lambda x: x[1], reverse=True)},
            "cost_by_provider": {k: round(v, 4) for k, v in sorted(by_provider.items(), key=lambda x: x[1], reverse=True)},
            "daily_costs": {k: round(v, 4) for k, v in sorted(daily_costs.items())},
            "trend": trend,
            "mrr": round(mrr, 4),
            "arr": round(arr, 4),
            "budget_alerts": self._get_budget_alerts(),
            "forecast_next_period": round(total_cost * 1.1, 4),
        }

    def _calculate_mrr(self, revenue_events: list) -> float:
        monthly = defaultdict(float)
        for r in revenue_events:
            if r.event_type in ("subscription_start", "subscription_renewal", "subscription_upgrade"):
                month_key = datetime.fromtimestamp(r.timestamp).strftime("%Y-%m")
                monthly[month_key] += r.amount
        if not monthly:
            return 0.0
        return sum(monthly.values()) / len(monthly)

    def _calculate_trend(self, daily_values: dict[str, float]) -> str:
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
        return []

    # ------------------------------------------------------------------
    # 5. Performance Analytics
    # ------------------------------------------------------------------
    def get_performance_analytics(self, days: int = 7, user_id: Optional[str] = None) -> dict:
        cutoff = time.time() - (days * 86400)
        events = [e for e in self._events if e.timestamp >= cutoff and e.event_type == "ai_request"]
        if user_id:
            events = [e for e in events if e.user_id == user_id]

        latencies = [e.metadata.get("latency", 0) for e in events]
        durations = [e.duration_ms for e in events if e.duration_ms > 0]

        latencies_sorted = sorted(latencies)
        durations_sorted = sorted(durations)

        by_model: dict[str, list[float]] = defaultdict(list)
        by_provider: dict[str, list[float]] = defaultdict(list)
        for e in events:
            model = e.metadata.get("model", "unknown")
            provider = e.metadata.get("provider", "unknown")
            latency = e.metadata.get("latency", 0)
            by_model[model].append(latency)
            by_provider[provider].append(latency)

        model_perf = {}
        for model, lats in by_model.items():
            s = sorted(lats)
            model_perf[model] = {
                "count": len(lats),
                "avg_latency": round(sum(lats) / len(lats), 3) if lats else 0,
                "p50_latency": round(s[len(s) // 2], 3) if s else 0,
                "p95_latency": round(s[int(len(s) * 0.95)], 3) if s else 0,
                "p99_latency": round(s[int(len(s) * 0.99)], 3) if s else 0,
            }

        return {
            "period_days": days,
            "total_requests": len(events),
            "avg_latency": round(sum(latencies) / max(len(latencies), 1), 3),
            "p50_latency": round(latencies_sorted[len(latencies_sorted) // 2], 3) if latencies_sorted else 0,
            "p95_latency": round(latencies_sorted[int(len(latencies_sorted) * 0.95)], 3) if latencies_sorted else 0,
            "p99_latency": round(latencies_sorted[int(len(latencies_sorted) * 0.99)], 3) if latencies_sorted else 0,
            "max_latency": round(max(latencies), 3) if latencies else 0,
            "min_latency": round(min(latencies), 3) if latencies else 0,
            "avg_duration_ms": round(sum(durations) / max(len(durations), 1), 1) if durations else 0,
            "performance_by_model": model_perf,
            "performance_by_provider": {
                p: {"count": len(lats), "avg_latency": round(sum(lats) / len(lats), 3)}
                for p, lats in by_provider.items()
            },
            "throughput_rpm": round(len(events) / max(days * 1440, 1), 4),
        }

    # ------------------------------------------------------------------
    # 6. Error Rate Analytics
    # ------------------------------------------------------------------
    def get_error_analytics(self, days: int = 7, user_id: Optional[str] = None) -> dict:
        cutoff = time.time() - (days * 86400)
        events = [e for e in self._events if e.timestamp >= cutoff]
        if user_id:
            events = [e for e in events if e.user_id == user_id]

        total = len(events)
        errors = [e for e in events if e.event_type == "error"]
        failed_requests = [e for e in events if e.event_type == "ai_request" and not e.metadata.get("success", True)]

        error_types: dict[str, int] = defaultdict(int)
        error_by_model: dict[str, int] = defaultdict(int)
        error_by_user: dict[str, int] = defaultdict(int)
        error_timeline: dict[str, int] = defaultdict(int)

        for e in errors:
            error_types[e.metadata.get("error_type", "unknown")] += 1
            error_by_user[e.user_id] += 1
            day_key = datetime.fromtimestamp(e.timestamp).strftime("%Y-%m-%d")
            error_timeline[day_key] += 1

        for e in failed_requests:
            model = e.metadata.get("model", "unknown")
            error_by_model[model] += 1

        total_requests = len([e for e in events if e.event_type == "ai_request"])
        error_rate = len(failed_requests) / max(total_requests, 1)

        return {
            "period_days": days,
            "total_events": total,
            "total_errors": len(errors),
            "total_failed_requests": len(failed_requests),
            "total_requests": total_requests,
            "error_rate": round(error_rate, 4),
            "error_rate_percent": round(error_rate * 100, 2),
            "error_types": dict(sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:20]),
            "errors_by_model": dict(sorted(error_by_model.items(), key=lambda x: x[1], reverse=True)[:10]),
            "errors_by_user": dict(sorted(error_by_user.items(), key=lambda x: x[1], reverse=True)[:10]),
            "error_timeline": dict(sorted(error_timeline.items())),
        }

    # ------------------------------------------------------------------
    # 6. GPU Utilization Analytics
    # ------------------------------------------------------------------
    def get_gpu_analytics(self, days: int = 7) -> dict:
        cutoff = time.time() - (days * 86400)
        metrics = [m for m in self._gpu_metrics if m.timestamp >= cutoff]
        if not metrics:
            return {
                "period_days": days,
                "gpu_available": False,
                "device_count": 0,
                "avg_utilization_percent": 0,
                "max_utilization_percent": 0,
                "avg_memory_used_mb": 0,
                "avg_memory_total_mb": 0,
                "avg_temperature_c": 0,
                "max_temperature_c": 0,
                "timeline": [],
            }

        device_ids = sorted({m.device_id for m in metrics})
        utilizations = [m.utilization_percent for m in metrics]
        mem_used = [m.memory_used_mb for m in metrics]
        mem_total = [m.memory_total_mb for m in metrics]
        temps = [m.temperature_c for m in metrics]

        timeline = []
        day_groups: dict[str, list] = defaultdict(list)
        for m in metrics:
            day = datetime.fromtimestamp(m.timestamp).strftime("%Y-%m-%d")
            day_groups[day].append(m)
        for day, day_metrics in sorted(day_groups.items()):
            timeline.append({
                "date": day,
                "avg_utilization_percent": round(sum(m.utilization_percent for m in day_metrics) / len(day_metrics), 2),
                "avg_memory_used_mb": round(sum(m.memory_used_mb for m in day_metrics) / len(day_metrics), 2),
                "avg_temperature_c": round(sum(m.temperature_c for m in day_metrics) / len(day_metrics), 2),
            })

        return {
            "period_days": days,
            "gpu_available": True,
            "device_count": len(device_ids),
            "device_ids": device_ids,
            "avg_utilization_percent": round(sum(utilizations) / len(utilizations), 2),
            "max_utilization_percent": round(max(utilizations), 2),
            "min_utilization_percent": round(min(utilizations), 2),
            "avg_memory_used_mb": round(sum(mem_used) / len(mem_used), 2),
            "avg_memory_total_mb": round(sum(mem_total) / len(mem_total), 2),
            "avg_temperature_c": round(sum(temps) / len(temps), 2),
            "max_temperature_c": round(max(temps), 2),
            "min_temperature_c": round(min(temps), 2),
            "timeline": timeline,
        }

    # ------------------------------------------------------------------
    # 7. Memory Usage Analytics
    # ------------------------------------------------------------------
    def get_memory_analytics(self, days: int = 7) -> dict:
        cutoff = time.time() - (days * 86400)
        metrics = [m for m in self._memory_metrics if m.timestamp >= cutoff]
        if not metrics:
            return {
                "period_days": days,
                "total_mb": 0,
                "avg_used_mb": 0,
                "avg_available_mb": 0,
                "avg_percent": 0,
                "max_percent": 0,
                "avg_swap_used_mb": 0,
                "timeline": [],
            }

        used = [m.used_mb for m in metrics]
        available = [m.available_mb for m in metrics]
        percents = [m.percent for m in metrics]
        swap = [m.swap_used_mb for m in metrics]

        timeline = []
        day_groups: dict[str, list] = defaultdict(list)
        for m in metrics:
            day = datetime.fromtimestamp(m.timestamp).strftime("%Y-%m-%d")
            day_groups[day].append(m)
        for day, day_metrics in sorted(day_groups.items()):
            timeline.append({
                "date": day,
                "used_mb": round(sum(m.used_mb for m in day_metrics) / len(day_metrics), 2),
                "available_mb": round(sum(m.available_mb for m in day_metrics) / len(day_metrics), 2),
                "percent": round(sum(m.percent for m in day_metrics) / len(day_metrics), 2),
                "swap_used_mb": round(sum(m.swap_used_mb for m in day_metrics) / len(day_metrics), 2),
            })

        return {
            "period_days": days,
            "total_mb": round(metrics[-1].total_mb, 2),
            "avg_used_mb": round(sum(used) / len(used), 2),
            "max_used_mb": round(max(used), 2),
            "min_used_mb": round(min(used), 2),
            "avg_available_mb": round(sum(available) / len(available), 2),
            "avg_percent": round(sum(percents) / len(percents), 2),
            "max_percent": round(max(percents), 2),
            "min_percent": round(min(percents), 2),
            "avg_swap_used_mb": round(sum(swap) / len(swap), 2),
            "max_swap_used_mb": round(max(swap), 2),
            "timeline": timeline,
        }

    # ------------------------------------------------------------------
    # 8. API Metrics Analytics
    # ------------------------------------------------------------------
    def get_api_metrics(self, days: int = 7, user_id: Optional[str] = None) -> dict:
        cutoff = time.time() - (days * 86400)
        metrics = [m for m in self._api_metrics if m.timestamp >= cutoff]
        if user_id:
            metrics = [m for m in metrics if m.user_id == user_id]

        total = len(metrics)
        errors = [m for m in metrics if m.status_code >= 400]
        latencies = [m.latency_ms for m in metrics if m.latency_ms > 0]

        by_endpoint: dict[str, dict] = defaultdict(lambda: {"count": 0, "errors": 0, "total_latency": 0.0, "total_tokens": 0})
        by_method: dict[str, int] = defaultdict(int)
        by_status: dict[str, int] = defaultdict(int)
        by_model: dict[str, dict] = defaultdict(lambda: {"count": 0, "total_latency": 0.0, "total_tokens": 0})

        for m in metrics:
            by_endpoint[m.endpoint]["count"] += 1
            by_method[m.method] += 1
            by_status[str(m.status_code)] += 1
            if m.status_code >= 400:
                by_endpoint[m.endpoint]["errors"] += 1
            by_endpoint[m.endpoint]["total_latency"] += m.latency_ms
            by_endpoint[m.endpoint]["total_tokens"] += m.tokens

            if m.model:
                by_model[m.model]["count"] += 1
                by_model[m.model]["total_latency"] += m.latency_ms
                by_model[m.model]["total_tokens"] += m.tokens

        endpoint_summary = {}
        for ep, data in by_endpoint.items():
            latencies_list = [m.latency_ms for m in metrics if m.endpoint == ep and m.latency_ms > 0]
            latencies_sorted = sorted(latencies_list)
            n = len(latencies_sorted)
            endpoint_summary[ep] = {
                "count": data["count"],
                "errors": data["errors"],
                "error_rate": round(data["errors"] / max(data["count"], 1), 4),
                "avg_latency_ms": round(data["total_latency"] / max(data["count"], 1), 2),
                "p95_latency_ms": round(latencies_sorted[int(n * 0.95)], 2) if n > 0 else 0,
                "p99_latency_ms": round(latencies_sorted[int(n * 0.99)], 2) if n > 0 else 0,
                "total_tokens": data["total_tokens"],
            }

        model_summary = {}
        for model, data in by_model.items():
            model_summary[model] = {
                "count": data["count"],
                "avg_latency_ms": round(data["total_latency"] / max(data["count"], 1), 2),
                "total_tokens": data["total_tokens"],
            }

        return {
            "period_days": days,
            "total_requests": total,
            "total_errors": len(errors),
            "error_rate": round(len(errors) / max(total, 1), 4),
            "avg_latency_ms": round(sum(latencies) / max(len(latencies), 1), 2) if latencies else 0,
            "by_endpoint": dict(sorted(endpoint_summary.items(), key=lambda x: x[1]["count"], reverse=True)[:20]),
            "by_method": dict(sorted(by_method.items())),
            "by_status": dict(sorted(by_status.items())),
            "by_model": dict(sorted(model_summary.items(), key=lambda x: x[1]["count"], reverse=True)[:10]),
        }

    # ------------------------------------------------------------------
    # 9. Feature Adoption Analytics
    # ------------------------------------------------------------------
    def track_feature_use(self, user_id: str, feature_name: str, category: str = "general"):
        now = time.time()
        key = f"{user_id}:{feature_name}"

        if key not in self._feature_adoption:
            self._feature_adoption[key] = FeatureAdoptionRecord(
                user_id=user_id,
                feature_name=feature_name,
                feature_category=category,
                first_used_at=now,
                last_used_at=now,
                usage_count=1,
            )
        else:
            record = self._feature_adoption[key]
            record.last_used_at = now
            record.usage_count += 1

            # Determine adoption (3+ uses within 7 days)
            if record.usage_count >= 3 and not record.is_adopted:
                if (now - record.first_used_at) <= 7 * 86400:
                    record.is_adopted = True
                    record.adoption_date = now
                    record.time_to_adoption_seconds = int(now - record.first_used_at)

    def get_feature_adoption_analytics(self, days: int = 30) -> dict:
        cutoff = time.time() - (days * 86400)
        features: dict[str, dict] = defaultdict(lambda: {
            "total_users": set(),
            "adopted_users": set(),
            "total_uses": 0,
            "category": "",
        })

        for key, record in self._feature_adoption.items():
            if record.first_used_at >= cutoff:
                f = features[record.feature_name]
                f["total_users"].add(record.user_id)
                if record.is_adopted:
                    f["adopted_users"].add(record.user_id)
                f["total_uses"] += record.usage_count
                f["category"] = record.feature_category

        result = {}
        for feature, data in features.items():
            total = len(data["total_users"])
            adopted = len(data["adopted_users"])
            result[feature] = {
                "total_users": total,
                "adopted_users": adopted,
                "adoption_rate": round(adopted / max(total, 1) * 100, 2),
                "total_uses": data["total_uses"],
                "avg_uses_per_user": round(data["total_uses"] / max(total, 1), 2),
                "category": data["category"],
            }

        return {
            "period_days": days,
            "features": dict(sorted(result.items(), key=lambda x: x[1]["total_users"], reverse=True)),
            "overall_adoption_rate": round(
                sum(d["adopted_users"] for d in features.values()) / max(sum(len(d["total_users"]) for d in features.values()), 1) * 100, 2
            ),
        }

    # ------------------------------------------------------------------
    # 8. Conversation Analytics
    # ------------------------------------------------------------------
    def track_conversation(self, conv: ConversationRecord):
        self._conversations.append(conv)
        self._persist_conversation(conv)

    def get_conversation_analytics(self, days: int = 7, user_id: Optional[str] = None) -> dict:
        cutoff = time.time() - (days * 86400)
        convs = [c for c in self._conversations if c.started_at >= cutoff]
        if user_id:
            convs = [c for c in convs if c.user_id == user_id]

        total_convs = len(convs)
        total_messages = sum(c.message_count for c in convs)
        total_tokens = sum(c.total_tokens for c in convs)
        total_cost = sum(c.total_cost for c in convs)
        avg_duration = sum(c.duration_seconds for c in convs) / max(total_convs, 1)
        avg_tokens = total_tokens / max(total_convs, 1)

        sentiments: dict[str, int] = defaultdict(int)
        for c in convs:
            sentiments[c.sentiment] += 1

        model_usage: dict[str, int] = defaultdict(int)
        for c in convs:
            model_usage[c.model] += 1

        return {
            "period_days": days,
            "total_conversations": total_convs,
            "total_messages": total_messages,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 4),
            "avg_messages_per_conversation": round(total_messages / max(total_convs, 1), 2),
            "avg_tokens_per_conversation": round(avg_tokens, 2),
            "avg_duration_seconds": round(avg_duration, 2),
            "sentiment_distribution": dict(sentiments),
            "model_distribution": dict(sorted(model_usage.items(), key=lambda x: x[1], reverse=True)),
            "satisfaction_avg": round(
                sum(c.satisfaction_score for c in convs if c.satisfaction_score is not None) / max(total_convs, 1), 2
            ),
        }

    # ------------------------------------------------------------------
    # 9. Model Performance Comparison
    # ------------------------------------------------------------------
    def get_model_performance_comparison(self, days: int = 7) -> dict:
        cutoff = time.time() - (days * 86400)
        events = [e for e in self._events if e.timestamp >= cutoff and e.event_type == "ai_request"]

        by_model: dict[str, dict] = defaultdict(lambda: {
            "count": 0,
            "success": 0,
            "fail": 0,
            "total_latency": 0.0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "latencies": [],
        })

        for e in events:
            model = e.metadata.get("model", "unknown")
            success = e.metadata.get("success", True)
            tokens = e.metadata.get("tokens", 0)
            latency = e.metadata.get("latency", 0)

            m = by_model[model]
            m["count"] += 1
            m["success" if success else "fail"] += 1
            m["total_latency"] += latency
            m["total_tokens"] += tokens
            m["latencies"].append(latency)

            input_tokens = int(tokens * 0.7)
            output_tokens = tokens - input_tokens
            costs = MODEL_COSTS.get(model, {"input": 0, "output": 0})
            m["total_cost"] += (costs["input"] * input_tokens + costs["output"] * output_tokens) / 1000

        result = {}
        for model, stats in by_model.items():
            lats = sorted(stats["latencies"])
            count = stats["count"]
            result[model] = {
                "requests": count,
                "success_rate": round(stats["success"] / max(count, 1) * 100, 2),
                "error_rate": round(stats["fail"] / max(count, 1) * 100, 2),
                "avg_latency": round(stats["total_latency"] / max(count, 1), 3),
                "p50_latency": round(lats[len(lats) // 2], 3) if lats else 0,
                "p95_latency": round(lats[int(len(lats) * 0.95)], 3) if lats else 0,
                "p99_latency": round(lats[int(len(lats) * 0.99)], 3) if lats else 0,
                "avg_tokens": round(stats["total_tokens"] / max(count, 1), 2),
                "total_cost": round(stats["total_cost"], 4),
            }

        return {
            "period_days": days,
            "models": result,
            "best_by_latency": min(result.items(), key=lambda x: x[1]["avg_latency"])[0] if result else None,
            "best_by_success": max(result.items(), key=lambda x: x[1]["success_rate"])[0] if result else None,
            "best_by_cost": min(result.items(), key=lambda x: x[1]["avg_tokens"])[0] if result else None,
        }

    # ------------------------------------------------------------------
    # 10. A/B Test Analytics
    # ------------------------------------------------------------------
    def create_ab_test(self, test: ABTestRecord):
        self._ab_tests[test.test_id] = test

    def assign_ab_test(self, assignment: ABTestAssignment):
        self._ab_assignments[f"{assignment.test_id}:{assignment.user_id}"] = assignment

    def track_ab_event(self, event: ABTestEvent):
        self._ab_events.append(event)
        self._persist_ab_event(event)

    def get_ab_test_analytics(self, test_id: str) -> dict:
        test = self._ab_tests.get(test_id)
        if not test:
            return {"error": "Test not found"}

        test_events = [e for e in self._ab_events if e.test_id == test_id]
        variant_a_events = [e for e in test_events if e.variant == "A"]
        variant_b_events = [e for e in test_events if e.variant == "B"]

        def aggregate(events):
            values = [e.event_value for e in events if e.event_value is not None]
            count = len(events)
            converted = len([e for e in events if e.event_value is not None and e.event_value > 0])
            return {
                "count": count,
                "conversions": converted,
                "conversion_rate": round(converted / max(count, 1) * 100, 2),
                "avg_value": round(sum(values) / max(len(values), 1), 4) if values else 0,
                "total_value": round(sum(values), 4),
            }

        a_stats = aggregate(variant_a_events)
        b_stats = aggregate(variant_b_events)

        significance = self._calculate_significance(a_stats, b_stats) if a_stats["count"] > 0 and b_stats["count"] > 0 else {}

        return {
            "test_id": test_id,
            "test_name": test.test_name,
            "status": test.status,
            "metric_name": test.metric_name,
            "variant_a": a_stats,
            "variant_b": b_stats,
            "sample_size_a": a_stats["count"],
            "sample_size_b": b_stats["count"],
            "statistical_significance": significance,
            "winner": self._determine_winner(a_stats, b_stats),
            "recommendation": self._generate_recommendation(a_stats, b_stats, significance),
        }

    def _calculate_significance(self, a: dict, b: dict) -> dict:
        if a["count"] < 2 or b["count"] < 2:
            return {"significant": False, "p_value": None}
        # Simplified z-test for proportions
        p1 = a["conversion_rate"] / 100
        p2 = b["conversion_rate"] / 100
        n1, n2 = a["count"], b["count"]
        p_pool = (a["conversions"] + b["conversions"]) / (n1 + n2)
        se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
        if se == 0:
            return {"significant": False, "p_value": 1.0}
        z = (p1 - p2) / se
        p_value = 2 * (1 - self._normal_cdf(abs(z)))
        return {"z_score": round(z, 4), "p_value": round(p_value, 4), "significant": p_value < 0.05}

    def _normal_cdf(self, x: float) -> float:
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def _determine_winner(self, a: dict, b: dict) -> Optional[str]:
        if a["count"] < 10 or b["count"] < 10:
            return "inconclusive"
        if a["conversion_rate"] > b["conversion_rate"]:
            return "A"
        elif b["conversion_rate"] > a["conversion_rate"]:
            return "B"
        return "tie"

    def _generate_recommendation(self, a: dict, b: dict, sig: dict) -> str:
        if not sig.get("significant"):
            return "Results are not yet statistically significant. Continue the test."
        winner = self._determine_winner(a, b)
        if winner == "inconclusive":
            return "Sample size is too small. Continue gathering data."
        return f"Variant {winner} shows statistically significant improvement. Consider rolling out Variant {winner}."

    # ------------------------------------------------------------------
    # 11. Cohort Analysis
    # ------------------------------------------------------------------
    def create_cohort(self, cohort: CohortRecord):
        self._cohorts[cohort.cohort_id] = cohort

    def add_cohort_member(self, member: CohortMember):
        self._cohort_members.append(member)
        self._persist_cohort_member(member)

    def get_cohort_analysis(self, cohort_id: str, days: int = 30) -> dict:
        cohort = self._cohorts.get(cohort_id)
        if not cohort:
            return {"error": "Cohort not found"}

        members = [m for m in self._cohort_members if m.cohort_id == cohort_id and m.is_active]
        cutoff = time.time() - (days * 86400)
        metrics = [m for m in self._cohort_metrics if m.cohort_id == cohort_id and datetime.strptime(m.date, "%Y-%m-%d").timestamp() >= cutoff]

        retention_matrix = self._build_retention_matrix(members)
        avg_retention = self._calculate_avg_retention(retention_matrix)

        return {
            "cohort_id": cohort_id,
            "cohort_name": cohort.cohort_name,
            "description": cohort.description,
            "member_count": len(members),
            "period_days": days,
            "retention_matrix": retention_matrix,
            "avg_retention_by_day": avg_retention,
            "daily_metrics": [
                {
                    "date": m.date,
                    "active_users": m.active_users,
                    "new_retained": m.new_retained,
                    "returning_users": m.returning_users,
                    "churned_users": m.churned_users,
                    "retention_rate": m.retention_rate,
                    "revenue": m.revenue,
                }
                for m in sorted(metrics, key=lambda x: x.date)
            ],
        }

    def _build_retention_matrix(self, members: list) -> dict:
        days = [0, 1, 3, 7, 14, 30, 60, 90]
        retention = {d: 0 for d in days}
        total = len(members)
        if total == 0:
            return retention

        snapshots = [s for s in self._retention_snapshots.values()
                     if any(s.user_id == m.user_id for m in members)]
        for d in days:
            retained = sum(1 for s in snapshots if getattr(s, f"day_{d}", False))
            retention[d] = round(retained / total * 100, 2)
        return retention

    def _calculate_avg_retention(self, matrix: dict) -> dict:
        return {f"day_{d}": v for d, v in matrix.items()}

    # ------------------------------------------------------------------
    # 12. Funnel Analysis
    # ------------------------------------------------------------------
    def create_funnel(self, funnel: FunnelRecord):
        self._funnels[funnel.funnel_id] = funnel

    def track_funnel_event(self, event: FunnelEvent):
        self._funnel_events.append(event)
        self._persist_funnel_event(event)

    def get_funnel_analytics(self, funnel_id: str, days: int = 30) -> dict:
        funnel = self._funnels.get(funnel_id)
        if not funnel:
            return {"error": "Funnel not found"}

        cutoff = time.time() - (days * 86400)
        events = [e for e in self._funnel_events if e.funnel_id == funnel_id and e.entered_at >= cutoff]

        steps = funnel.steps
        step_counts: dict[int, dict] = defaultdict(lambda: {"entered": 0, "completed": 0, "dropped": 0})
        drop_off_reasons: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for e in events:
            step_counts[e.step_index]["entered"] += 1
            if e.completed:
                step_counts[e.step_index]["completed"] += 1
            else:
                step_counts[e.step_index]["dropped"] += 1
                if e.drop_off_reason:
                    drop_off_reasons[e.step_index][e.drop_off_reason] += 1

        step_analysis = []
        prev_completion = len(events)
        for i, step in enumerate(steps):
            entered = step_counts[i]["entered"]
            completed = step_counts[i]["completed"]
            dropped = step_counts[i]["dropped"]
            conversion_rate = (completed / max(prev_completion, 1)) * 100 if prev_completion > 0 else 0
            step_analysis.append({
                "step_index": i,
                "step_name": step.get("name", f"Step {i+1}"),
                "entered": entered,
                "completed": completed,
                "dropped": dropped,
                "conversion_rate": round(conversion_rate, 2),
                "overall_conversion": round(completed / max(len(events), 1) * 100, 2),
                "top_drop_off_reasons": dict(sorted(drop_off_reasons[i].items(), key=lambda x: x[1], reverse=True)[:5]),
            })
            prev_completion = completed

        overall_completion = step_counts[len(steps) - 1]["completed"] if steps else 0
        total_entered = len(events)

        return {
            "funnel_id": funnel_id,
            "funnel_name": funnel.funnel_name,
            "period_days": days,
            "total_entries": total_entered,
            "overall_completion_rate": round(overall_completion / max(total_entered, 1) * 100, 2),
            "steps": step_analysis,
            "biggest_drop_off": max(step_analysis, key=lambda s: s["dropped"])["step_name"] if step_analysis else None,
        }

    # ------------------------------------------------------------------
    # 13. Retention Analytics
    # ------------------------------------------------------------------
    def update_retention_snapshot(self, snapshot: RetentionSnapshot):
        key = f"{snapshot.user_id}:{snapshot.cohort_date}"
        self._retention_snapshots[key] = snapshot
        self._persist_retention_snapshot(snapshot)

    def get_retention_analytics(self, cohort_date: str, days: int = 90) -> dict:
        snapshots = [s for s in self._retention_snapshots.values() if s.cohort_date == cohort_date]
        if not snapshots:
            return {"error": "No retention data for this cohort"}

        retention_days = [0, 1, 3, 7, 14, 30, 60, 90]
        retention_by_day = {}
        for d in retention_days:
            if d > days:
                continue
            retained = sum(1 for s in snapshots if getattr(s, f"day_{d}", False))
            retention_by_day[f"day_{d}"] = round(retained / max(len(snapshots), 1) * 100, 2)

        churn_rate = 100 - retention_by_day.get("day_30", 0)
        return {
            "cohort_date": cohort_date,
            "cohort_size": len(snapshots),
            "period_days": days,
            "retention_by_day": retention_by_day,
            "day_1_retention": retention_by_day.get("day_1", 0),
            "day_7_retention": retention_by_day.get("day_7", 0),
            "day_30_retention": retention_by_day.get("day_30", 0),
            "churn_rate_30d": round(churn_rate, 2),
            "stickiness": round(retention_by_day.get("day_1", 0) / 100 * 4.5, 2),
        }

    # ------------------------------------------------------------------
    # 14. Revenue Analytics
    # ------------------------------------------------------------------
    def track_revenue(self, event: RevenueEvent):
        self._revenue_events.append(event)
        self._persist_revenue_event(event)

    def get_revenue_analytics(self, days: int = 30, user_id: Optional[str] = None) -> dict:
        cutoff = time.time() - (days * 86400)
        events = [e for e in self._revenue_events if e.timestamp >= cutoff]
        if user_id:
            events = [e for e in events if e.user_id == user_id]

        by_type: dict[str, dict] = defaultdict(lambda: {"count": 0, "total": 0.0})
        by_plan: dict[str, dict] = defaultdict(lambda: {"count": 0, "total": 0.0})
        by_day: dict[str, float] = defaultdict(float)
        by_user: dict[str, float] = defaultdict(float)

        for e in events:
            by_type[e.event_type]["count"] += 1
            by_type[e.event_type]["total"] += e.amount
            if e.plan_name:
                by_plan[e.plan_name]["count"] += 1
                by_plan[e.plan_name]["total"] += e.amount
            day_key = datetime.fromtimestamp(e.timestamp).strftime("%Y-%m-%d")
            by_day[day_key] += e.amount
            by_user[e.user_id] += e.amount

        total_revenue = sum(e.amount for e in events)
        refunds = sum(e.amount for e in events if e.event_type == "refund")
        net_revenue = total_revenue - refunds

        return {
            "period_days": days,
            "total_revenue": round(total_revenue, 4),
            "net_revenue": round(net_revenue, 4),
            "refunds": round(refunds, 4),
            "revenue_by_type": {k: {"count": v["count"], "total": round(v["total"], 4)} for k, v in by_type.items()},
            "revenue_by_plan": {k: {"count": v["count"], "total": round(v["total"], 4)} for k, v in sorted(by_plan.items(), key=lambda x: x[1]["total"], reverse=True)},
            "daily_revenue": {k: round(v, 4) for k, v in sorted(by_day.items())},
            "top_customers": dict(sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:20]),
            "mrr": round(self._calculate_mrr(events), 4),
            "arr": round(self._calculate_mrr(events) * 12, 4),
            "arpu": round(total_revenue / max(len({e.user_id for e in events}), 1), 4),
        }

    # ------------------------------------------------------------------
    # 15. Custom Report Builder
    # ------------------------------------------------------------------
    def create_custom_report(self, report: CustomReport):
        self._custom_reports[report.report_id] = report
        self._persist_custom_report(report)

    def run_custom_report(self, report_id: str, days: int = 30) -> dict:
        report = self._custom_reports.get(report_id)
        if not report:
            return {"error": "Report not found"}

        config = report.config
        metrics = config.get("metrics", [])
        dimensions = config.get("dimensions", [])
        filters = config.get("filters", {})

        result = {"report_id": report_id, "report_name": report.report_name, "generated_at": datetime.now(timezone.utc).isoformat()}

        for metric in metrics:
            if metric == "usage":
                result["usage"] = self.get_usage_stats(days=days)
            elif metric == "tokens":
                result["tokens"] = self.get_token_analytics(days=days)
            elif metric == "costs":
                result["costs"] = self.get_cost_analytics(days=days)
            elif metric == "performance":
                result["performance"] = self.get_performance_analytics(days=days)
            elif metric == "errors":
                result["errors"] = self.get_error_analytics(days=days)
            elif metric == "conversations":
                result["conversations"] = self.get_conversation_analytics(days=days)
            elif metric == "revenue":
                result["revenue"] = self.get_revenue_analytics(days=days)
            elif metric == "feature_adoption":
                result["feature_adoption"] = self.get_feature_adoption_analytics(days=days)
            elif metric == "retention":
                cohort_date = filters.get("cohort_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
                result["retention"] = self.get_retention_analytics(cohort_date=cohort_date, days=days)
            elif metric == "model_performance":
                result["model_performance"] = self.get_model_performance_comparison(days=days)
            elif metric == "user_behavior":
                result["user_behavior"] = self.get_user_behavior_analytics(days=days)
            elif metric == "realtime":
                result["realtime"] = self.get_realtime_dashboard(days=min(days, 1))

        report.last_run_at = time.time()
        return result

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    def track_request(self, user_id: str, model: str, provider: str, tokens: int = 0, latency: float = 0.0, success: bool = True, session_id: str = "", page_url: str = "", duration_ms: int = 0):
        now = time.time()
        event = AnalyticsEvent(
            event_type="ai_request",
            user_id=user_id,
            timestamp=now,
            metadata={"model": model, "provider": provider, "tokens": tokens, "latency": latency, "success": success},
            session_id=session_id,
            page_url=page_url,
            duration_ms=duration_ms,
        )
        self._events.append(event)

        if user_id not in self._sessions:
            self._sessions[user_id] = {"started_at": now, "last_activity": now, "event_count": 0}
        self._sessions[user_id]["last_activity"] = now
        self._sessions[user_id]["event_count"] += 1

        self._persist_event("ai_request", user_id, event.metadata)

    def track_error(self, user_id: str, error_type: str, details: str = "", session_id: str = ""):
        now = time.time()
        event = AnalyticsEvent(
            event_type="error",
            user_id=user_id,
            timestamp=now,
            metadata={"error_type": error_type, "details": details},
            session_id=session_id,
        )
        self._events.append(event)

        self._persist_event("error", user_id, event.metadata)

    def track_user_action(self, user_id: str, action: str, metadata: dict = None, session_id: str = ""):
        now = time.time()
        event = AnalyticsEvent(
            event_type="user_action",
            user_id=user_id,
            timestamp=now,
            metadata=metadata or {},
            session_id=session_id,
        )
        self._events.append(event)
        if user_id not in self._sessions:
            self._sessions[user_id] = {"started_at": now, "last_activity": now, "event_count": 0}
        self._sessions[user_id]["last_activity"] = now
        self._sessions[user_id]["event_count"] += 1

        self._persist_event("user_action", user_id, event.metadata)

    def record_event(self, event_type: str, user_id: str, metadata: dict = None):
        self.track_user_action(user_id, event_type, metadata)

    def track_gpu_utilization(self, device_id: int = 0, utilization_percent: float = 0.0, memory_used_mb: float = 0.0, memory_total_mb: float = 0.0, temperature_c: float = 0.0):
        metric = GPUMetric(
            device_id=device_id,
            utilization_percent=utilization_percent,
            memory_used_mb=memory_used_mb,
            memory_total_mb=memory_total_mb,
            temperature_c=temperature_c,
            timestamp=time.time(),
        )
        self._gpu_metrics.append(metric)
        self._persist_gpu_metric(metric)

    def track_memory_usage(self, total_mb: float = 0.0, used_mb: float = 0.0, available_mb: float = 0.0, percent: float = 0.0, swap_used_mb: float = 0.0):
        metric = MemoryMetric(
            total_mb=total_mb,
            used_mb=used_mb,
            available_mb=available_mb,
            percent=percent,
            swap_used_mb=swap_used_mb,
            timestamp=time.time(),
        )
        self._memory_metrics.append(metric)
        self._persist_memory_metric(metric)

    def track_api_metric(self, endpoint: str, method: str, status_code: int, latency_ms: float = 0.0, user_id: str = "", model: str = "", provider: str = "", tokens: int = 0):
        metric = APIMetric(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            latency_ms=latency_ms,
            user_id=user_id,
            model=model,
            provider=provider,
            tokens=tokens,
            timestamp=time.time(),
        )
        self._api_metrics.append(metric)
        self._persist_api_metric(metric)

    def get_user_stats(self, user_id: str) -> dict:
        user_events = [e for e in self._events if e.user_id == user_id]
        total_events = len(user_events)
        event_type_counts: dict[str, int] = defaultdict(int)
        for e in user_events:
            event_type_counts[e.event_type] += 1
        return {
            "total_events": total_events,
            "event_types": dict(sorted(event_type_counts.items(), key=lambda x: x[1], reverse=True)),
        }

    def get_usage_stats(self, days: int = 7) -> dict:
        cutoff = time.time() - (days * 86400)
        events = [e for e in self._events if e.timestamp >= cutoff]
        total_requests = len([e for e in events if e.event_type == "ai_request"])
        total_errors = len([e for e in events if e.event_type == "error"])
        total_tokens = sum(e.metadata.get("tokens", 0) for e in events if e.event_type == "ai_request")
        total_latency = sum(e.metadata.get("latency", 0) for e in events if e.event_type == "ai_request")

        return {
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_errors": total_errors,
            "error_rate": round(total_errors / max(total_requests, 1), 4),
            "average_latency": round(total_latency / max(total_requests, 1), 3),
            "active_users": len({e.user_id for e in events if e.timestamp >= cutoff}),
            "total_users": len(self._sessions),
        }

    def get_provider_breakdown(self) -> dict:
        breakdown: dict[str, int] = defaultdict(int)
        for e in self._events:
            if e.event_type == "ai_request":
                provider = e.metadata.get("provider", "unknown")
                breakdown[provider] += 1
        return dict(sorted(breakdown.items(), key=lambda x: x[1], reverse=True))

    def get_model_breakdown(self) -> dict:
        breakdown: dict[str, int] = defaultdict(int)
        for e in self._events:
            if e.event_type == "ai_request":
                model = e.metadata.get("model", "unknown")
                breakdown[model] += 1
        return dict(sorted(breakdown.items(), key=lambda x: x[1], reverse=True))

    def get_daily_usage(self, days: int = 30) -> dict:
        result: dict[str, int] = {}
        cutoff = time.time() - (days * 86400)
        events = [e for e in self._events if e.timestamp >= cutoff and e.event_type == "ai_request"]
        for e in events:
            day_key = datetime.fromtimestamp(e.timestamp).strftime("%Y-%m-%d")
            result[day_key] = result.get(day_key, 0) + 1
        return dict(sorted(result.items()))

    def get_ai_usage_analytics(self, days: int = 7) -> dict:
        cutoff = time.time() - (days * 86400)
        events = [e for e in self._events if e.timestamp >= cutoff and e.event_type == "ai_request"]

        by_model: dict[str, int] = defaultdict(int)
        by_provider: dict[str, int] = defaultdict(int)
        by_user: dict[str, int] = defaultdict(int)
        total_success = 0
        total_fail = 0
        total_latency = 0.0

        for e in events:
            model = e.metadata.get("model", "unknown")
            provider = e.metadata.get("provider", "unknown")
            by_model[model] += 1
            by_provider[provider] += 1
            by_user[e.user_id] += 1
            if e.metadata.get("success", True):
                total_success += 1
            else:
                total_fail += 1
            total_latency += e.metadata.get("latency", 0.0)

        count = len(events)
        return {
            "period_days": days,
            "total_requests": count,
            "successful_requests": total_success,
            "failed_requests": total_fail,
            "success_rate": round(total_success / max(count, 1) * 100, 2),
            "average_latency": round(total_latency / max(count, 1), 3),
            "requests_by_model": dict(sorted(by_model.items(), key=lambda x: x[1], reverse=True)),
            "requests_by_provider": dict(sorted(by_provider.items(), key=lambda x: x[1], reverse=True)),
            "active_users": len(by_user),
            "top_users": sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:10],
        }

    def get_search_analytics(self, days: int = 7) -> dict:
        return {
            "period_days": days,
            "total_queries": 0,
            "click_through_rate": 0.0,
            "zero_result_queries": 0,
            "zero_result_rate": 0.0,
            "avg_latency_ms": 0.0,
            "top_queries": [],
            "zero_result_query_list": [],
        }

    def get_knowledge_analytics(self, days: int = 7) -> dict:
        return {
            "period_days": days,
            "documents_indexed": 0,
            "entities_extracted": 0,
            "relationships_created": 0,
            "knowledge_base_size": 0,
        }

    def get_workflow_analytics(self, days: int = 7) -> dict:
        return {
            "period_days": days,
            "total_executions": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "success_rate": 0.0,
            "agents": [],
        }

    def get_agent_analytics(self, days: int = 7) -> dict:
        return {
            "period_days": days,
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "success_rate": 0.0,
            "agents": [],
        }

    def get_user_analytics(self, days: int = 7) -> dict:
        cutoff = time.time() - (days * 86400)
        events = [e for e in self._events if e.timestamp >= cutoff]

        active_users = len({e.user_id for e in events})
        event_counts: dict[str, int] = defaultdict(int)
        for e in events:
            event_counts[e.event_type] += 1

        return {
            "period_days": days,
            "active_users": active_users,
            "total_actions": len(events),
            "top_users": [],
            "engagement_by_category": dict(sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
        }

    def get_overview(self, days: int = 7) -> dict:
        usage = self.get_usage_stats(days=days)
        ai = self.get_ai_usage_analytics(days=days)
        tokens = self.get_token_analytics(days=days)
        costs = self.get_cost_analytics(days=days)
        models = self.get_model_performance_comparison(days=days)
        users = self.get_user_analytics(days=days)

        return {
            "period_days": days,
            "usage": {
                "total_requests": usage.get("total_requests", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "active_users": usage.get("active_users", 0),
                "avg_latency": usage.get("average_latency", 0),
                "error_rate": usage.get("error_rate", 0),
            },
            "ai_usage": {
                "total_requests": ai.get("total_requests", 0),
                "success_rate": ai.get("success_rate", 0),
                "avg_latency": ai.get("average_latency", 0),
            },
            "tokens": {
                "total_tokens": tokens.get("total_tokens", 0),
                "total_cost": tokens.get("total_cost", 0),
            },
            "costs": {
                "total_cost": costs.get("total_api_cost", costs.get("total_cost", 0)),
                "trend": costs.get("trend", "stable"),
            },
            "models": {
                "model_count": len(models.get("models", {})),
                "best_by_latency": models.get("best_by_latency"),
                "best_by_success": models.get("best_by_success"),
            },
            "users": {
                "active_users": users.get("active_users", 0),
                "total_actions": users.get("total_actions", 0),
            },
        }

    def get_dashboard_data(self, days: int = 7) -> dict:
        conversations = self.get_conversation_analytics(days=days)
        costs = self.get_cost_analytics(days=days)
        return {
            "total_messages": conversations.get("total_messages", 0),
            "total_cost_usd": costs.get("total_api_cost", costs.get("total_cost", 0)),
            "realtime": self.get_realtime_dashboard(days=min(days, 1)),
            "usage": self.get_usage_stats(days=days),
            "tokens": self.get_token_analytics(days=days),
            "costs": costs,
            "performance": self.get_performance_analytics(days=days),
            "errors": self.get_error_analytics(days=days),
            "conversations": conversations,
            "models": self.get_model_performance_comparison(days=days),
            "feature_adoption": self.get_feature_adoption_analytics(days=days),
            "user_behavior": self.get_user_behavior_analytics(days=days),
            "revenue": self.get_revenue_analytics(days=days),
        }

    def export_analytics(self, days: int = 30, format: str = "json") -> dict:
        cutoff = time.time() - (days * 86400)
        events = [e for e in self._events if e.timestamp >= cutoff]

        export_data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "period_days": days,
            "overview": self.get_dashboard_data(days=days),
            "events": [
                {
                    "event_type": e.event_type,
                    "user_id": e.user_id,
                    "timestamp": datetime.fromtimestamp(e.timestamp).isoformat(),
                    "metadata": e.metadata,
                    "session_id": e.session_id,
                    "page_url": e.page_url,
                    "duration_ms": e.duration_ms,
                }
                for e in events
            ],
            "behavior_events": [
                {
                    "user_id": e.user_id,
                    "event_type": e.event_type,
                    "page_url": e.page_url,
                    "element_id": e.element_id,
                    "time_on_page_seconds": e.time_on_page_seconds,
                    "timestamp": datetime.fromtimestamp(e.timestamp).isoformat(),
                }
                for e in self._behavior_events if e.timestamp >= cutoff
            ],
            "revenue_events": [
                {
                    "user_id": e.user_id,
                    "event_type": e.event_type,
                    "amount": e.amount,
                    "timestamp": datetime.fromtimestamp(e.timestamp).isoformat(),
                }
                for e in self._revenue_events if e.timestamp >= cutoff
            ],
        }
        return export_data


# Singleton
advanced_analytics = AdvancedAnalyticsEngine()
