"""Temporal computing: time-travel debugging, temporal databases, timelines, state management, and temporal AI.

Quick start:
    from app.temporal import TimeTravelDebugger, TemporalDatabase, ConversationTimeline
    from app.temporal import ImmutableStateTree, StatePredictor, TimeAwareContextWindow

    debugger = TimeTravelDebugger(event_store)
    db = TemporalDatabase()
    timeline = ConversationTimeline("conv-1")
"""

from .state_manager import (
    ImmutableState,
    ImmutableStateTree,
    StateDiffer,
    StatePredictor,
    GSet,
    PNCounter,
    LWWRegister,
    ORSet,
    ConsistencyManager,
)
from .temporal_db import (
    TemporalDatabase,
    TemporalEventStore,
    CommandHandler,
    QueryHandler,
    TemporalConstraintEngine,
    AuditBlockchain,
    LineageTracker,
    TemporalEntity,
    AuditRecord,
    LineageNode,
    OperationType,
    ConsistencyLevel,
    TemporalConstraint,
    Command,
    Query,
    QueryResult,
)
from .cqrs import (
    CQRS,
    CommandBus,
    QueryBus,
    EventSourcedAggregate,
    CommandError,
    Middleware,
)
from .temporal_ai import (
    TimeAwareContextWindow,
    TemporalToken,
    TemporalAttention,
    HistoricalPatternRecognizer,
    TemporalPattern,
    TimeSeriesForecaster,
)
from .time_travel import (
    TimeTravelDebugger,
    SnapshotStore,
    StateSnapshot,
    TimelineEvent,
    TimelineBranch,
    TemporalBreakpoint,
    BreakpointType,
    Direction,
    get_debugger,
)
from .timeline import (
    ConversationTimeline,
    DecisionTree,
    ScenarioAnalyzer,
    ScenarioResult,
    CausalChainAnalyzer,
    CausalLink,
    TimelineExporter,
    TimelineNode,
)
from .engine import TemporalEngine

__all__ = [
    "TimeTravelDebugger",
    "SnapshotStore",
    "StateSnapshot",
    "TimelineEvent",
    "TimelineBranch",
    "TemporalBreakpoint",
    "BreakpointType",
    "Direction",
    "get_debugger",
    "TemporalDatabase",
    "TemporalEventStore",
    "CommandHandler",
    "QueryHandler",
    "TemporalConstraintEngine",
    "AuditBlockchain",
    "LineageTracker",
    "TemporalEntity",
    "AuditRecord",
    "LineageNode",
    "OperationType",
    "ConsistencyLevel",
    "TemporalConstraint",
    "Command",
    "Query",
    "QueryResult",
    "ConversationTimeline",
    "DecisionTree",
    "ScenarioAnalyzer",
    "ScenarioResult",
    "CausalChainAnalyzer",
    "CausalLink",
    "TimelineExporter",
    "TimelineNode",
    "ImmutableStateTree",
    "ImmutableState",
    "StateDiffer",
    "StatePredictor",
    "GSet",
    "PNCounter",
    "LWWRegister",
    "ORSet",
    "ConsistencyManager",
    "TimeAwareContextWindow",
    "TemporalToken",
    "TemporalAttention",
    "HistoricalPatternRecognizer",
    "TemporalPattern",
    "TimeSeriesForecaster",
    "TemporalEngine",
    "CQRS",
    "CommandBus",
    "QueryBus",
    "EventSourcedAggregate",
    "CommandError",
    "Middleware",
]
