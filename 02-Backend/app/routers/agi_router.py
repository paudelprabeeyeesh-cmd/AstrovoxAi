import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.agi_orchestrator import _agi_orchestrator
from app.recursive_planning import RecursivePlanningService
from app.self_evolution import SelfEvolutionService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agi"])

recursive_planning = RecursivePlanningService()
self_evolution = SelfEvolutionService()


class GoalRequest(BaseModel):
    goal: str
    context: dict[str, Any] | None = None


class PlanRequest(BaseModel):
    goal: str
    max_depth: int = 5
    context: dict[str, Any] | None = None


class ReflectionRequest(BaseModel):
    target: str
    feedback: str


class EngineActionRequest(BaseModel):
    engine: str
    payload: dict[str, Any] = {}


class ModuleActionRequest(BaseModel):
    module: str
    action: str
    args: dict[str, Any] = {}


@router.post("/agi/goals/achieve")
async def achieve_goal(req: GoalRequest):
    result = _agi_orchestrator.execute_goal(req.goal, req.context)
    return result


@router.post("/agi/planning/recursive")
async def create_recursive_plan(req: PlanRequest):
    result = recursive_planning.create_plan(req.goal, max_depth=req.max_depth, context=req.context)
    return result


@router.post("/agi/planning/refine")
async def refine_plan(plan_id: str, feedback: str):
    result = recursive_planning.refine(plan_id, feedback)
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Plan not found")
    return result


@router.get("/agi/planning/plans")
async def list_plans():
    return {"plans": recursive_planning.list_plans()}


@router.get("/agi/planning/plans/{plan_id}")
async def get_plan(plan_id: str):
    plan = recursive_planning.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.post("/agi/planning/execute")
async def execute_plan_step(plan_id: str, step_id: str):
    result = recursive_planning.execute_step(plan_id, step_id)
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Plan or step not found")
    return result


@router.post("/agi/reflection/improve")
async def reflect_and_improve(req: ReflectionRequest):
    result = _agi_orchestrator.improve(req.target, req.feedback)
    return result


@router.post("/agi/reasoning/query")
async def query_reasoning(req: EngineActionRequest):
    result = _agi_orchestrator.reason_about(req.engine, req.payload)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/agi/reasoning/engines")
async def list_reasoning_engines():
    return {"engines": _agi_orchestrator.reasoning.list_engines()}


@router.post("/agi/self-evolution/act")
async def act_self_evolution(req: ModuleActionRequest):
    try:
        result = _agi_orchestrator.evolve(req.module, req.action, req.args)
        return {"module": req.module, "action": req.action, "result": result}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("Self-evolution action failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/agi/self-evolution/modules")
async def list_self_evolution_modules():
    return {"modules": list(self_evolution.modules.keys())}
