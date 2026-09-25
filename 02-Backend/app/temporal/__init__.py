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
from .snapshots import (
    SnapshotEngine,
    Snapshot,
    StatePoint,
)
from .cqrs import (
    CQRS,
    CommandBus,
    QueryBus,
    EventSourcedAggregate,
)
from .time_travel_api import (
    TimeTravelAPI,
    PointInTimeQuery,
)
from .reverse_debugger import (
    ReverseDebugger,
    DebugSession,
)
from .branching import (
    TimelineBranch,
    BranchTimelineManager,
    Branch,
)
from .causal import (
    CausalChainAnalyzer as CausalChainAnalyzerN,
    CausalEvent as CausalEventN,
    CausalEdge as CausalEdgeN,
)
from .diffing import (
    StateDiffer as StateDifferN,
    HistoricalDiff as HistoricalDiffN,
    DiffResult as DiffResultN,
)
from .rollback import (
    RollbackAutomation,
    RollbackPlan,
    RollbackResult,
)
from .debugger import (
    TimeTravelDebugger as TimeTravelDebuggerN,
    TimeSlice,
    DebuggerAPI,
)

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
    "SnapshotEngine",
    "Snapshot",
    "StatePoint",
    "CQRS",
    "CommandBus",
    "QueryBus",
    "EventSourcedAggregate",
    "TimeTravelAPI",
    "PointInTimeQuery",
    "ReverseDebugger",
    "DebugSession",
    "TimelineBranch",
    "BranchTimelineManager",
    "Branch",
    "CausalChainAnalyzerN",
    "CausalEventN",
    "CausalEdgeN",
    "StateDifferN",
    "HistoricalDiffN",
    "DiffResultN",
    "RollbackAutomation",
    "RollbackPlan",
    "RollbackResult",
    "TimeTravelDebuggerN",
    "TimeSlice",
    "DebuggerAPI",
]
