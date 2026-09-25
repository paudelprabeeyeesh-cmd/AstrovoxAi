from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from ..multiverse.engine import MultiverseEngine
from ..multiverse.models import (
    BranchType,
    RealityEditRequest,
    ContinuumManipulationRequest,
    ConstructorBlueprint,
    ConstructorRunRequest,
    RecursiveBranchRequest,
    PortalNavigateRequest,
)
from ...utils.auth.auth_utils import get_user_id_from_token

router = APIRouter(prefix="/multiverse", tags=["multiverse"])
engine = MultiverseEngine()


class CreateTimelineRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    branch_type: str = Field("conversation", pattern="^(conversation|scenario|parallel|divergence)$")


class ForkUniverseRequest(BaseModel):
    timeline_id: str
    name: str = Field(min_length=1, max_length=200)
    prompt_variant: Optional[str] = None
    model_override: Optional[str] = None
    temperature_override: Optional[float] = Field(None, ge=0, le=2)
    fork_point_message_id: Optional[int] = None


class SendMessageRequest(BaseModel):
    universe_id: str
    content: str = Field(min_length=1, max_length=4000)
    role: str = Field("user", pattern="^(user|assistant|system)$")
    model_used: Optional[str] = None


class ScenarioRequest(BaseModel):
    universe_id: str
    scenario_id: str
    variables: Dict[str, Any] = Field(default_factory=dict)
    iterations: int = Field(1, ge=1, le=100)
    compare_against: Optional[str] = None


class ParallelRequest(BaseModel):
    universe_id: str
    variants: List[Dict[str, Any]] = Field(min_items=1, max_items=10)


class MergeRequest(BaseModel):
    source_universe_id: str
    target_universe_id: str
    strategy: str = Field("prefer_target", pattern="^(prefer_source|prefer_target|interleave|diff_only)$")
    conflict_resolution: Optional[str] = Field(None, pattern="^(source|target|newest|manual)$")


class ImportTimelineRequest(BaseModel):
    payload: Dict[str, Any]


@router.post("/timelines")
async def create_timeline(request: CreateTimelineRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    try:
        from ..multiverse.models import BranchType
        branch_type = BranchType(request.branch_type)
    except Exception:
        branch_type = BranchType.CONVERSATION
    timeline = engine.create_timeline(user_id=user_id, name=request.name, description=request.description, branch_type=branch_type)
    return {"status": "OK", "timeline": timeline.dict()}


@router.get("/timelines")
async def list_timelines(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    timelines = engine.list_timelines(user_id)
    return {"status": "OK", "timelines": [t.dict() for t in timelines]}


@router.get("/timelines/{timeline_id}")
async def get_timeline(timeline_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    timeline = engine.get_timeline(timeline_id, user_id)
    if not timeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found")
    return {"status": "OK", "timeline": timeline.dict()}


@router.post("/universes/fork")
async def fork_universe(request: ForkUniverseRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    universe = engine.fork_universe(
        timeline_id=request.timeline_id,
        user_id=user_id,
        name=request.name,
        prompt_variant=request.prompt_variant,
        model_override=request.model_override,
        temperature_override=request.temperature_override,
        fork_point_message_id=request.fork_point_message_id,
    )
    if not universe:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to fork universe")
    return {"status": "OK", "universe": universe.dict()}


@router.post("/universes/message")
async def send_universe_message(request: SendMessageRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    message = engine.send_message(request.universe_id, user_id, request.role, request.content, model_used=request.model_used)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Universe not found")
    return {"status": "OK", "message": message}


@router.get("/universes/{universe_id}/messages")
async def get_universe_messages(universe_id: str, limit: int = 100, offset: int = 0, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    messages = engine.get_messages(universe_id, user_id, limit=limit, offset=offset)
    return {"status": "OK", "messages": messages, "count": len(messages)}


@router.post("/scenarios/run")
async def run_scenario(request: ScenarioRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    results = engine.run_what_if_scenario(
        universe_id=request.universe_id,
        user_id=user_id,
        scenario_id=request.scenario_id,
        variables=request.variables,
        iterations=request.iterations,
        compare_against=request.compare_against,
    )
    return {"status": "OK", "results": [r.dict() for r in results]}


@router.post("/parallel/run")
async def run_parallel(request: ParallelRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    try:
        run = engine.run_parallel_variants(request.universe_id, user_id, request.variants)
        return {"status": "OK", "run": run.dict()}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/universes/merge")
async def merge_universes(request: MergeRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    diff = engine.merge_universes(
        source_universe_id=request.source_universe_id,
        target_universe_id=request.target_universe_id,
        user_id=user_id,
        strategy=request.strategy,
        conflict_resolution=request.conflict_resolution,
    )
    if not diff:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to merge universes")
    return {"status": "OK", "diff": diff.dict()}


@router.get("/timelines/{timeline_id}/visualization")
async def get_visualization(timeline_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    viz = engine.get_visualization(timeline_id, user_id)
    if not viz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found")
    return {"status": "OK", "visualization": viz}


@router.get("/timelines/{timeline_id}/export")
async def export_timeline(timeline_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    payload = engine.export_timeline(timeline_id, user_id)
    if not payload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found")
    return {"status": "OK", "export": payload}


@router.post("/timelines/import")
async def import_timeline(request: ImportTimelineRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    timeline = engine.import_timeline(user_id, request.payload)
    if not timeline:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to import timeline")
    return {"status": "OK", "timeline": timeline.dict()}


@router.delete("/universes/{universe_id}")
async def collapse_universe(universe_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    ok = engine.collapse_universe(universe_id, user_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Universe not found")
    return {"status": "OK", "message": "Universe collapsed"}


@router.get("/universes/{universe_id}/debug")
async def debug_meta_reality(universe_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    debug = engine.debug_meta_reality(universe_id, user_id)
    if "error" in debug:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=debug["error"])
    return {"status": "OK", "debug": debug}


@router.put("/universes/{universe_id}/edit")
async def edit_reality(universe_id: str, request: RealityEditRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    updated = engine.edit_reality(universe_id, user_id, request.dict(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Universe not found")
    return {"status": "OK", "universe": updated}


@router.post("/universes/{universe_id}/continuum")
async def manipulate_continuum(universe_id: str, request: ContinuumManipulationRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    result = engine.manipulate_continuum(universe_id, user_id, request.dict(exclude_none=True))
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Universe not found")
    return {"status": "OK", "continuum": result}


@router.post("/constructors/run")
async def run_constructor(request: ConstructorRunRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    universe = engine.construct_universe(user_id, request.timeline_id, request.blueprint.dict())
    if not universe:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Timeline not found")
    return {"status": "OK", "universe": universe.dict()}


@router.post("/recursive/branch")
async def recursive_branch(request: RecursiveBranchRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    universes = engine.run_safe_recursive_branch(
        universe_id=request.universe_id,
        user_id=user_id,
        max_depth=request.max_depth,
        branching_factor=request.branching_factor,
        prompt_variants=request.prompt_variants,
        model_override=request.model_override,
    )
    return {"status": "OK", "universes": [u.dict() for u in universes], "count": len(universes)}


@router.post("/portal/navigate")
async def portal_navigate(request: PortalNavigateRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    result = engine.portal_navigate(request.universe_id, user_id, request.target_universe_id, request.merge_on_arrival)
    if not result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Portal navigation failed")
    return {"status": "OK", "portal": result}
