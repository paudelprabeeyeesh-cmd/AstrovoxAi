from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class UniverseStatus(str, Enum):
    ACTIVE = "active"
    FORKED = "forked"
    MERGED = "merged"
    COLLAPSED = "collapsed"
    PAUSED = "paused"


class BranchType(str, Enum):
    CONVERSATION = "conversation"
    SCENARIO = "scenario"
    PARALLEL = "parallel"
    DIVERGENCE = "divergence"


class TimelineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    base_universe_id: Optional[str] = None
    branch_type: BranchType = BranchType.CONVERSATION
    parameters: Dict[str, Any] = Field(default_factory=dict)


class TimelineFork(BaseModel):
    universe_id: str
    fork_point_message_id: Optional[int] = None
    prompt_variant: Optional[str] = None
    model_override: Optional[str] = None
    temperature_override: Optional[float] = Field(None, ge=0, le=2)


class ScenarioRun(BaseModel):
    universe_id: str
    scenario_id: str
    variables: Dict[str, Any] = Field(default_factory=dict)
    iterations: int = Field(1, ge=1, le=100)
    compare_against: Optional[str] = None


class ParallelVariant(BaseModel):
    universe_id: str
    model: str
    system_prompt_override: Optional[str] = None
    temperature: float = Field(0.7, ge=0, le=2)
    label: Optional[str] = Field(None, max_length=100)


class MergeRequest(BaseModel):
    source_universe_id: str
    target_universe_id: str
    strategy: str = Field("prefer_target", regex="^(prefer_source|prefer_target|interleave|diff_only)$")
    conflict_resolution: Optional[str] = Field(None, regex="^(source|target|newest|manual)$")


class DivergenceQuery(BaseModel):
    universe_a: str
    universe_b: str
    start_message_id: Optional[int] = None
    end_message_id: Optional[int] = None


class Universe(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    status: UniverseStatus = UniverseStatus.ACTIVE
    branch_type: BranchType = BranchType.CONVERSATION
    parent_universe_id: Optional[str] = None
    root_universe_id: Optional[str] = None
    generation: int = 0
    parameters: Dict[str, Any] = Field(default_factory=dict)
    message_count: int = 0
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Timeline(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    root_universe_id: str
    universes: List[Universe] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DivergencePoint(BaseModel):
    id: str
    universe_a: str
    universe_b: str
    message_id: int
    content_a: str
    content_b: str
    similarity: float = Field(ge=0, le=1)
    divergence_type: str
    created_at: datetime


class ScenarioResult(BaseModel):
    id: str
    scenario_id: str
    universe_id: str
    iteration: int
    result: Dict[str, Any]
    tokens_used: int
    latency_ms: int
    created_at: datetime


class ParallelRun(BaseModel):
    id: str
    universe_id: str
    variants: List[Dict[str, Any]]
    results: List[Dict[str, Any]]
    status: str
    created_at: datetime


class UniverseDiff(BaseModel):
    id: str
    source_universe_id: str
    target_universe_id: str
    diff: List[Dict[str, Any]]
    summary: str
    created_at: datetime
