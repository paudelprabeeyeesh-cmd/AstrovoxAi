"""Temporal computing API routes.

Exposes time-travel debugging, temporal database, timeline, state management,
and temporal AI endpoints.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from app.temporal import (
    BreakpointType,
    Command,
    CommandHandler,
    ConsistencyLevel,
    ConversationTimeline,
    CausalChainAnalyzer,
    DecisionTree,
    Direction,
    GSet,
    HistoricalPatternRecognizer,
    ImmutableStateTree,
    LWWRegister,
    ORSet,
    PNCounter,
    OperationType,
    Query,
    QueryHandler,
    QueryResult,
    ScenarioAnalyzer,
    StatePredictor,
    StateSnapshot,
    TemporalAttention,
    TemporalBreakpoint,
    TemporalDatabase,
    TimeAwareContextWindow,
    TimeSeriesForecaster,
    TimeTravelDebugger,
    TimelineExporter,
    TimelineNode,
    get_debugger,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/temporal", tags=["temporal"])


@router.get("/health")
async def temporal_health():
    return {"status": "ok", "module": "temporal"}


# Shared instances
_db = TemporalDatabase()
_debugger = get_debugger("api")
_state_tree = ImmutableStateTree()
_predictor = StatePredictor()
_context_window = TimeAwareContextWindow()
_attention = TemporalAttention()
_pattern_recognizer = HistoricalPatternRecognizer()
_forecaster = TimeSeriesForecaster()


# ---------------------------------------------------------------------------
# Time-travel debugging
# ---------------------------------------------------------------------------


class CaptureSnapshotRequest(BaseModel):
    state: Dict[str, Any]
    label: str = ""
    event_id: Optional[str] = None


class CreateBranchRequest(BaseModel):
    name: str
    from_snapshot_id: Optional[str] = None
    created_by: str = "system"


class SetBreakpointRequest(BaseModel):
    breakpoint_id: str
    breakpoint_type: str
    target: Any
    description: str = ""
    condition: Optional[Dict[str, Any]] = None


@router.post("/debug/capture-snapshot")
def capture_snapshot(request: CaptureSnapshotRequest):
    snap = _debugger.capture_snapshot(request.state, label=request.label, event_id=request.event_id)
    return {"snapshot": snap.to_dict()}


@router.post("/debug/restore-snapshot")
def restore_snapshot(snapshot_id: str = Body(..., embed=True)):
    try:
        state = _debugger.restore_snapshot(snapshot_id)
        return {"state": state}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/debug/snapshots")
def list_snapshots(branch_id: Optional[str] = None):
    return _debugger.list_snapshots(branch_id)


@router.post("/debug/branch")
def create_branch(request: CreateBranchRequest):
    branch_id = _debugger.create_branch(request.name, from_snapshot_id=request.from_snapshot_id, created_by=request.created_by)
    return {"branch_id": branch_id}


@router.post("/debug/switch-branch")
def switch_branch(branch_id: str = Body(..., embed=True)):
    _debugger.switch_branch(branch_id)
    return {"branch_id": branch_id}


@router.get("/debug/branches")
def list_branches():
    return _debugger.list_branches()


@router.post("/debug/breakpoint")
def set_breakpoint(request: SetBreakpointRequest):
    bp = TemporalBreakpoint(
        breakpoint_id=request.breakpoint_id,
        breakpoint_type=BreakpointType(request.breakpoint_type),
        target=request.target,
        description=request.description,
    )
    _debugger.set_breakpoint(bp)
    return {"breakpoint_id": request.breakpoint_id}


@router.get("/debug/breakpoints")
def list_breakpoints():
    return _debugger.list_breakpoints()


@router.delete("/debug/breakpoint/{breakpoint_id}")
def remove_breakpoint(breakpoint_id: str):
    ok = _debugger.remove_breakpoint(breakpoint_id)
    if not ok:
        raise HTTPException(status_code=404, detail="breakpoint not found")
    return {"removed": True}


@router.post("/debug/step-forward")
def step_forward(event: Dict[str, Any] = Body(...)):
    from app.temporal.time_travel import TimelineEvent
    evt = TimelineEvent(
        event_id=event.get("event_id", "evt"),
        timestamp=datetime.now(timezone.utc),
        position=event.get("position", 0),
        event_type=event.get("event_type", ""),
        payload=event.get("payload", {}),
        branch_id=_debugger.get_current_branch(),
    )
    def apply(state, ev):
        state["last_event"] = ev.event_type
        state["position"] = ev.position
        return state
    state = _debugger.step_forward(evt, apply)
    return {"state": state}


@router.post("/debug/step-backward")
def step_backward(steps: int = Body(1, embed=True)):
    state = _debugger.step_backward(steps)
    return {"state": state}


@router.get("/debug/compare")
def compare_snapshots(snapshot_id_a: str, snapshot_id_b: str):
    diff = _debugger.compare_snapshots(snapshot_id_a, snapshot_id_b)
    return {"diff": diff}


@router.get("/debug/visualize-branch")
def visualize_branch(branch_id: str = "main"):
    return _debugger.visualize_branch(branch_id)


@router.get("/debug/stats")
def debugger_stats():
    return _debugger.get_stats()


# ---------------------------------------------------------------------------
# Temporal database
# ---------------------------------------------------------------------------


@router.post("/db/apply")
def temporal_apply(
    entity_id: str = Body(...),
    operation: str = Body(...),
    data: Dict[str, Any] = Body(...),
    actor: str = Body("system"),
    entity_type: str = Body("entity"),
    old_state: Optional[Dict[str, Any]] = Body(None),
):
    try:
        entity = _db.apply(
            entity_id=entity_id,
            operation=OperationType(operation),
            new_state=data,
            actor=actor,
            entity_type=entity_type,
            old_state=old_state,
        )
        return {"entity": entity.to_dict()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/db/query")
def temporal_query(entity_id: str, as_of: Optional[str] = None):
    target_time = datetime.fromisoformat(as_of) if as_of else None
    state = _db.query(entity_id, as_of=target_time)
    if state is None:
        raise HTTPException(status_code=404, detail="entity not found")
    return {"entity_id": entity_id, "state": state}


@router.get("/db/history")
def temporal_history(entity_id: str, limit: int = 100):
    return _db.history(entity_id, limit=limit)


@router.get("/db/audit")
def audit_trail(entity_id: str, limit: int = 100):
    return _db.audit_trail(entity_id, limit=limit)


@router.get("/db/lineage")
def data_lineage(entity_id: str):
    return _db.lineage(entity_id)


@router.post("/db/constraint")
def register_constraint(
    constraint_id: str = Body(...),
    entity_type: str = Body(...),
    rule: str = Body(...),
    description: str = Body(""),
):
    def validator(new_state, old_state):
        return entity_type in new_state.get("types", [])
    _db._constraints.register(TemporalConstraint(
        constraint_id=constraint_id,
        entity_type=entity_type,
        rule=rule,
        validator=validator,
        description=description,
    ))
    return {"registered": True}


@router.get("/db/verify-audit")
def verify_audit():
    return {"valid": _db.verify_audit_integrity()}


@router.get("/db/stats")
def db_stats():
    return _db.stats()


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------


@router.post("/timeline/create")
def create_timeline(conversation_id: str = Body(..., embed=True)):
    timeline = ConversationTimeline(conversation_id)
    return {"conversation_id": conversation_id}


@router.post("/timeline/add-message")
def add_message(
    conversation_id: str = Body(...),
    role: str = Body(...),
    content: str = Body(...),
    parent_node_id: Optional[str] = Body(None),
    branch_id: Optional[str] = Body(None),
):
    timeline = ConversationTimeline(conversation_id)
    node = timeline.add_message(role=role, content=content, parent_node_id=parent_node_id, branch_id=branch_id)
    return {"node": node.to_dict()}


@router.post("/timeline/branch")
def branch_timeline(conversation_id: str = Body(...), name: str = Body(...), from_node_id: str = Body(...)):
    timeline = ConversationTimeline(conversation_id)
    branch_id = timeline.branch(name, from_node_id)
    return {"branch_id": branch_id}


@router.post("/timeline/merge")
def merge_branches(conversation_id: str = Body(...), source_branch_id: str = Body(...), target_branch_id: str = Body(...), merge_node_id: str = Body(...)):
    timeline = ConversationTimeline(conversation_id)
    node = timeline.merge(source_branch_id, target_branch_id, merge_node_id)
    return {"node": node.to_dict()}


@router.get("/timeline/visualize")
def visualize_timeline(conversation_id: str, branch_id: Optional[str] = None):
    timeline = ConversationTimeline(conversation_id)
    return timeline.visualize(branch_id)


@router.get("/timeline/divergence")
def detect_divergence(conversation_id: str, branch_a: str = Body(...), branch_b: str = Body(...)):
    timeline = ConversationTimeline(conversation_id)
    node = timeline.detect_divergence(branch_a, branch_b)
    return {"divergence_node_id": node}


@router.post("/timeline/export")
def export_timeline(conversation_id: str = Body(...), format: str = Body("json")):
    timeline = ConversationTimeline(conversation_id)
    exporter = TimelineExporter(timeline)
    if format == "csv":
        return {"data": exporter.to_csv(), "format": "csv"}
    return {"data": exporter.to_json(), "format": "json"}


@router.post("/timeline/import")
def import_timeline(data: str = Body(...), format: str = Body("json")):
    if format == "csv":
        raise HTTPException(status_code=400, detail="CSV import not supported in this endpoint")
    timeline = TimelineExporter.from_json(data)
    return {"conversation_id": timeline._conversation_id}


@router.post("/timeline/causal-chain")
def causal_chain(conversation_id: str = Body(...), start_node_id: str = Body(...)):
    timeline = ConversationTimeline(conversation_id)
    analyzer = CausalChainAnalyzer(timeline)
    analyzer.add_link(start_node_id, "effect-1", "causes")
    return analyzer.analyze(start_node_id)


# ---------------------------------------------------------------------------
# Decision tree / scenario analysis
# ---------------------------------------------------------------------------


@router.post("/decision-tree/create")
def create_decision_tree(tree_id: str = Body(..., embed=True)):
    tree = DecisionTree(tree_id)
    return {"tree_id": tree_id}


@router.post("/decision-tree/add-decision")
def add_decision(tree_id: str = Body(...), parent_node_id: Optional[str] = Body(None), content: Dict[str, Any] = Body(...)):
    tree = DecisionTree(tree_id)
    node = tree.add_decision(parent_node_id, content)
    return {"node": node.to_dict()}


@router.post("/decision-tree/add-outcome")
def add_outcome(tree_id: str = Body(...), parent_decision_id: str = Body(...), content: Dict[str, Any] = Body(...)):
    tree = DecisionTree(tree_id)
    node = tree.add_outcome(parent_decision_id, content)
    return {"node": node.to_dict()}


@router.get("/decision-tree/visualize")
def visualize_decision_tree(tree_id: str):
    tree = DecisionTree(tree_id)
    return tree.visualize()


@router.post("/scenario/simulate")
def simulate_scenario(conversation_id: str = Body(...), scenario_id: str = Body(...), branch_id: str = Body(...)):
    timeline = ConversationTimeline(conversation_id)
    analyzer = ScenarioAnalyzer(timeline)
    def sim(nodes):
        return {"nodes_analyzed": len(nodes), "score": 0.75}
    result = analyzer.simulate(scenario_id, branch_id, sim)
    return {"scenario": result.__dict__}


@router.get("/scenario/list")
def list_scenarios(conversation_id: str):
    timeline = ConversationTimeline(conversation_id)
    analyzer = ScenarioAnalyzer(timeline)
    return analyzer.list_scenarios()


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------


@router.post("/state/commit")
def commit_state(path: str = Body(...), data: Dict[str, Any] = Body(...), metadata: Optional[Dict[str, Any]] = Body(None)):
    state = _state_tree.commit(path, data, metadata=metadata)
    return {"state": state.to_dict()}


@router.get("/state/get")
def get_state(path: str):
    state = _state_tree.get(path)
    if state is None:
        raise HTTPException(status_code=404, detail="state not found")
    return {"path": path, "state": state}


@router.get("/state/history")
def state_history(path: str, limit: int = 100):
    return _state_tree.history(path, limit=limit)


@router.post("/state/rollback")
def rollback_state(path: str = Body(...), steps: int = Body(1)):
    state = _state_tree.rollback(path, steps)
    if state is None:
        raise HTTPException(status_code=400, detail="rollback not possible")
    return {"path": path, "state": state}


@router.post("/state/diff")
def state_diff(state_id_a: str = Body(...), state_id_b: str = Body(...), path: str = Body("default")):
    try:
        diff = _state_tree.diff(path, state_id_a, state_id_b)
        return {"diff": diff}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/state/optimize")
def optimize_state(path: str = Body(..., embed=True)):
    return _state_tree.optimize(path)


@router.post("/state/predict")
def predict_state(path: str = Body(...), steps: int = Body(1)):
    current = _state_tree.get(path)
    if current is None:
        raise HTTPException(status_code=404, detail="state not found")
    predictions = _predictor.predict(current, steps=steps)
    return {"predictions": predictions}


# ---------------------------------------------------------------------------
# CRDTs
# ---------------------------------------------------------------------------


@router.post("/crdt/gset/add")
def gset_add(items: List[Any] = Body(...)):
    gset = GSet()
    for item in items:
        gset.add(item)
    return {"elements": list(gset.elements())}


@router.post("/crdt/pn-counter/increment")
def pn_counter_increment():
    counter = PNCounter()
    counter.increment()
    counter.decrement()
    return {"value": counter.value()}


@router.post("/crdt/lww/set")
def lww_set(value: Any = Body(...), node_id: str = Body("node-1")):
    reg = LWWRegister(node_id)
    reg.set(value)
    return {"value": reg.get()}


@router.post("/crdt/or-set/add")
def orset_add(items: List[Any] = Body(...)):
    orset = ORSet()
    for item in items:
        orset.add(item)
    return {"elements": [item for item in orset._items if orset.has(item)]}


# ---------------------------------------------------------------------------
# Temporal AI
# ---------------------------------------------------------------------------


@router.post("/ai/context/add")
def add_context_token(text: str = Body(...), metadata: Optional[Dict[str, Any]] = Body(None)):
    token = _context_window.add(text, metadata=metadata)
    return {"token_id": token.token_id, "timestamp": token.timestamp.isoformat()}


@router.get("/ai/context")
def get_context(max_tokens: Optional[int] = None):
    text = _context_window.context_text(max_tokens=max_tokens)
    return {"context": text, "size": _context_window.size()}


@router.post("/ai/attention")
def temporal_attention(query: Dict[str, Any] = Body(...), keys: List[Dict[str, Any]] = Body(...), timestamps: List[str] = Body(...)):
    ts = [datetime.fromisoformat(t) for t in timestamps]
    results = _attention.attend(query, keys, ts)
    return {"attended": [{"key": k, "score": s} for k, s in results]}


@router.post("/ai/patterns/detect")
def detect_patterns(sequences: List[List[str]] = Body(...)):
    _pattern_recognizer = HistoricalPatternRecognizer()
    for seq in sequences:
        _pattern_recognizer.observe(seq)
    patterns = _pattern_recognizer.detect_patterns()
    return {"patterns": [p.__dict__ for p in patterns]}


@router.post("/ai/forecast")
def forecast(series_id: str = Body(...), horizon: int = Body(5)):
    now = datetime.now(timezone.utc)
    for i in range(10):
        _forecaster.observe(series_id, datetime.fromtimestamp(now.timestamp() + i * 60, tz=timezone.utc), float(i))
    forecast = _forecaster.forecast(series_id, horizon=horizon)
    return {"series_id": series_id, "forecast": [(ts.isoformat(), v) for ts, v in forecast]}


@router.get("/ai/forecast/stats")
def forecast_stats(series_id: str):
    return _forecaster.series_stats(series_id)


# ---------------------------------------------------------------------------
# State management stats
# ---------------------------------------------------------------------------


@router.get("/state/stats")
def state_stats():
    return _state_tree.stats()


@router.get("/stats")
def temporal_stats():
    return {
        "debugger": _debugger.get_stats(),
        "database": _db.stats(),
        "state": _state_tree.stats(),
        "context_window": {"size": _context_window.size()},
        "patterns": _pattern_recognizer.stats(),
    }
