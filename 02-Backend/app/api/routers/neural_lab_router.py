"""Authenticated API for the isolated, CPU-first Neural Lab."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import tempfile
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials
from neural_lab.config import TinyTransformerConfig
from neural_lab.datasets import MAX_DATASET_BYTES, DatasetStore
from neural_lab.resources import enforce_memory_budget
from neural_lab.tokenizer import CharacterTokenizer
from pydantic import BaseModel, Field

from app.utils.auth.auth_utils import get_current_user, security_scheme

router = APIRouter(prefix="/neural-lab", tags=["neural-lab"])
logger = logging.getLogger(__name__)
_ID = re.compile(r"^[0-9a-f]{32}$")
_active: dict[str, threading.Event] = {}
_active_lock = threading.Lock()


class TrainRequest(BaseModel):
    dataset_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    resume_job_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$")
    context_length: int = Field(default=32, ge=8, le=256)
    hidden_size: int = Field(default=16, ge=8, le=128)
    num_layers: int = Field(default=1, ge=1, le=4)
    num_heads: int = Field(default=2, ge=1, le=8)
    batch_size: int = Field(default=1, ge=1, le=8)
    max_steps: int = Field(default=10, ge=1, le=2000)
    checkpoint_interval: int = Field(default=5, ge=1, le=2000)
    seed: int = Field(default=17, ge=0, le=2147483647)
    memory_budget_mib: int = Field(default=256, ge=16, le=1024)
    reserve_memory_mib: int = Field(default=1536, ge=256, le=3072)
    optimizer: str = Field(default="adamw", pattern=r"^(adamw|adam|sgd)$")


class RegisterModelRequest(BaseModel):
    job_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    name: str = Field(min_length=1, max_length=80)


class EvaluateRequest(BaseModel):
    dataset_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    max_batches: int = Field(default=32, ge=1, le=128)


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    max_new_tokens: int = Field(default=64, ge=1, le=256)
    temperature: float = Field(default=1.0, ge=0.05, le=2.0, allow_inf_nan=False)
    top_k: int | None = Field(default=None, ge=1, le=64)


async def _user_context(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),  # noqa: B008
    user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
):
    """Create a request-scoped Supabase client so concurrent requests cannot swap JWTs."""
    client = _authenticated_client(credentials.credentials)
    try:
        yield user, client
    finally:
        _close_client(client)


def _authenticated_client(token: str):
    from supabase import create_client

    url = os.getenv("VITE_SUPABASE_URL")
    key = os.getenv("VITE_SUPABASE_ANON_KEY") or os.getenv("VITE_SUPABASE_PUBLISHABLE_KEY")
    if not url or not key:
        raise HTTPException(status_code=503, detail="Supabase is not configured")
    client = create_client(url, key)
    client.postgrest.auth(token)
    return client


def _close_client(client) -> None:
    postgrest = getattr(client, "postgrest", None)
    session = getattr(postgrest, "session", None)
    close = getattr(session, "close", None)
    if close:
        close()


USER_CONTEXT = Depends(_user_context)


def _storage(user_id: str) -> tuple[Path, DatasetStore]:
    root = Path(os.getenv("NEURAL_LAB_STORAGE_ROOT", "./astrovox_neural_lab")).expanduser().resolve()
    user_root = (root / user_id).resolve()
    if not user_root.is_relative_to(root):
        raise HTTPException(status_code=400, detail="Invalid user storage scope")
    user_root.mkdir(parents=True, exist_ok=True)
    return user_root, DatasetStore(user_root / "datasets")


def _dataset_record(client, user_id: str, dataset_id: str) -> dict:
    result = (client.table("neural_lab_datasets").select("*")
              .eq("user_id", user_id).eq("id", dataset_id).limit(1).execute())
    if not result.data:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return result.data[0]


@router.get("/datasets")
async def list_datasets(context=USER_CONTEXT):
    user, client = context
    result = client.table("neural_lab_datasets").select(
        "id,name,digest,metadata,created_at"
    ).eq("user_id", user["id"]).order("created_at", desc=True).execute()
    return {"datasets": result.data or []}


@router.post("/datasets", status_code=201)
async def upload_dataset(
    file: UploadFile = File(...),  # noqa: B008
    provenance: str = Form(..., min_length=1, max_length=2000),
    license_note: str = Form(..., min_length=1, max_length=2000),
    preview_characters: int = Form(500, ge=0, le=4096),
    context=USER_CONTEXT,
):
    user, client = context
    if Path(file.filename or "").suffix.lower() not in {".txt", ".md"}:
        raise HTTPException(status_code=415, detail="Upload a UTF-8 .txt or .md file")
    root, store = _storage(user["id"])
    staged_path = None
    try:
        fd, name = tempfile.mkstemp(prefix="upload-", suffix=Path(file.filename).suffix.lower(), dir=root)
        staged_path = Path(name)
        size = 0
        with os.fdopen(fd, "wb") as target:
            while chunk := await file.read(64 * 1024):
                size += len(chunk)
                if size > MAX_DATASET_BYTES:
                    raise HTTPException(status_code=413, detail=f"Dataset exceeds {MAX_DATASET_BYTES} bytes")
                target.write(chunk)
        metadata = store.add_file(staged_path, provenance=provenance, license_note=license_note,
                                  preview_characters=preview_characters)
        existing = (client.table("neural_lab_datasets").select("id").eq("user_id", user["id"])
                    .eq("digest", metadata["dataset_id"]).limit(1).execute())
        row = {"id": existing.data[0]["id"] if existing.data else uuid.uuid4().hex,
               "user_id": user["id"], "name": Path(file.filename).stem[:120],
               "digest": metadata["dataset_id"], "metadata": metadata}
        if not existing.data:
            client.table("neural_lab_datasets").insert(row).execute()
        return {
            "dataset_id": row["id"], "bytes": metadata["size_bytes"],
            "characters": metadata["character_count"], "lines": metadata["line_count"],
            "unique_characters": metadata["unique_character_count"],
            **{key: metadata[key] for key in ("preview", "provenance", "license_note", "created_at")},
        }
    except HTTPException:
        raise
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        if staged_path:
            staged_path.unlink(missing_ok=True)
        await file.close()


@router.delete("/datasets/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: str, context=USER_CONTEXT):
    user, client = context
    if not _ID.fullmatch(dataset_id):
        raise HTTPException(status_code=400, detail="Invalid dataset id")
    record = _dataset_record(client, user["id"], dataset_id)
    linked = (client.table("neural_lab_jobs").select("id").eq("user_id", user["id"])
              .eq("dataset_id", dataset_id).execute())
    with _active_lock:
        if any(item["id"] in _active for item in (linked.data or [])):
            raise HTTPException(status_code=409, detail="A running job is using this dataset")
    _, store = _storage(user["id"])
    client.table("neural_lab_datasets").delete().eq("user_id", user["id"]).eq("id", dataset_id).execute()
    store.delete(record["digest"], confirmed=True)


def _persist_job_progress(client, user_id: str, job_id: str, run_path: Path) -> None:
    try:
        progress = json.loads((run_path / "job.json").read_text(encoding="utf-8"))
        client.table("neural_lab_jobs").update({
            "status": progress.get("state", "PREPARING"),
            "progress": progress,
            "updated_at": datetime.now(UTC).isoformat(),
        }).eq("id", job_id).eq("user_id", user_id).execute()
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read Neural Lab progress job_id=%s error_type=%s", job_id, type(exc).__name__)
    except Exception as exc:
        logger.warning("Could not persist Neural Lab progress job_id=%s error_type=%s", job_id, type(exc).__name__)


def _mark_stale_job(client, user_id: str, job_id: str, status: str, detail: str) -> None:
    try:
        client.table("neural_lab_jobs").update({
            "status": status, "error": detail, "updated_at": datetime.now(UTC).isoformat(),
        }).eq("id", job_id).eq("user_id", user_id).execute()
    except Exception as exc:
        logger.warning("Could not mark stale Neural Lab job job_id=%s error_type=%s", job_id, type(exc).__name__)


async def _run_training(token: str, user_id: str, job_id: str, dataset_path: Path, run_path: Path,
                        config: dict, cancel: threading.Event, resume_from: Path | None):
    from neural_lab.training import train_tiny_model

    client = None
    try:
        client = _authenticated_client(token)
    except Exception as exc:
        logger.warning("Neural Lab progress persistence unavailable job_id=%s error_type=%s", job_id, type(exc).__name__)
    training = asyncio.create_task(asyncio.to_thread(
        train_tiny_model, dataset_path, run_path,
        context_length=config["context_length"], hidden_size=config["hidden_size"],
        num_layers=config["num_layers"], num_heads=config["num_heads"],
        batch_size=config["batch_size"], max_steps=config["max_steps"],
        checkpoint_interval=config["checkpoint_interval"],
        seed=config["seed"],
        memory_budget_mib=config["memory_budget_mib"], reserve_memory_mib=config["reserve_memory_mib"],
        optimizer_name=config["optimizer"], cancel_event=cancel, resume_from=resume_from, job_id=job_id,
    ))
    while not training.done():
        await asyncio.sleep(2)
        if client is not None:
            await asyncio.to_thread(_persist_job_progress, client, user_id, job_id, run_path)
    try:
        await training
        progress = json.loads((run_path / "job.json").read_text(encoding="utf-8"))
        status = progress.get("state", "FAILED")
        detail = progress.get("error")
    except Exception as exc:
        status = "FAILED"
        detail = str(exc)[:1000]
        try:
            progress = json.loads((run_path / "job.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            progress = {"state": status, "error": detail}
    finally:
        with _active_lock:
            _active.pop(job_id, None)
    if client is not None:
        try:
            client.table("neural_lab_jobs").update({
                "status": status, "error": detail, "progress": progress,
                "updated_at": datetime.now(UTC).isoformat(),
            }).eq("id", job_id).eq("user_id", user_id).execute()
        except Exception as exc:
            logger.warning("Could not persist Neural Lab job state job_id=%s error_type=%s", job_id, type(exc).__name__)
        finally:
            _close_client(client)


@router.post("/jobs", status_code=202)
async def start_job(
    request: TrainRequest,
    background: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),  # noqa: B008
    context=USER_CONTEXT,
):
    user, client = context
    user_root, store = _storage(user["id"])
    record = _dataset_record(client, user["id"], request.dataset_id)
    resume_from = None
    resume_job_id = request.resume_job_id
    if resume_job_id:
        previous = (client.table("neural_lab_jobs").select("run_path,status,dataset_id")
                    .eq("user_id", user["id"]).eq("id", resume_job_id).limit(1).execute())
        if not previous.data:
            raise HTTPException(status_code=404, detail="Resume job not found")
        previous = previous.data[0]
        if previous["dataset_id"] != request.dataset_id:
            raise HTTPException(status_code=422, detail="Resume with the same dataset")
        runs_root = (user_root / "runs").resolve()
        old_run = Path(previous["run_path"]).resolve()
        if not old_run.is_relative_to(runs_root):
            raise HTTPException(status_code=400, detail="Invalid resume storage path")
        try:
            old_job = json.loads((old_run / "job.json").read_text(encoding="utf-8"))
            old_state = old_job.get("state")
            with _active_lock:
                still_running = resume_job_id in _active
            if old_state not in {"CANCELLED", "FAILED"} and not (
                old_state in {"QUEUED", "PREPARING", "TRAINING", "VALIDATING", "CHECKPOINTING"}
                and not still_running
            ):
                raise HTTPException(status_code=409, detail="Only cancelled, failed, or interrupted jobs can be resumed")
            resume_from = Path(old_job["checkpoints"][-1]).resolve(strict=True)
            if not resume_from.is_relative_to(old_run) or not resume_from.is_file():
                raise ValueError("resume checkpoint is outside the job directory")
        except HTTPException:
            raise
        except (OSError, KeyError, IndexError, json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="No valid checkpoint is available to resume") from exc
    try:
        dataset_path = store.get_path(record["digest"])
        tokenizer = CharacterTokenizer.from_file(dataset_path)
        config = TinyTransformerConfig(
            vocab_size=tokenizer.vocab_size, context_length=request.context_length, hidden_size=request.hidden_size,
            num_layers=request.num_layers, num_heads=request.num_heads, batch_size=request.batch_size,
            memory_budget_mib=request.memory_budget_mib, reserve_memory_mib=request.reserve_memory_mib,
        )
        memory = enforce_memory_budget(config)
    except (ValueError, FileNotFoundError, MemoryError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    job_id = uuid.uuid4().hex
    run_path = (_storage(user["id"])[0] / "runs" / job_id).resolve()
    run_root = (_storage(user["id"])[0] / "runs").resolve()
    if not run_path.is_relative_to(run_root):
        raise HTTPException(status_code=400, detail="Invalid run path")
    run_path.mkdir(parents=True, exist_ok=False)
    values = request.model_dump()
    values.pop("dataset_id")
    values.pop("resume_job_id")
    row = {"id": job_id, "user_id": user["id"], "dataset_id": request.dataset_id,
           "config": {**values, "vocab_size": tokenizer.vocab_size,
                      "estimated_parameter_count": memory.parameter_count}, "status": "QUEUED",
           "run_path": str(run_path), "error": None}
    try:
        client.table("neural_lab_jobs").insert(row).execute()
    except Exception as exc:
        run_path.rmdir()
        raise HTTPException(status_code=503, detail="Could not persist the training job") from exc
    cancel = threading.Event()
    with _active_lock:
        if _active:
            client.table("neural_lab_jobs").delete().eq("id", job_id).eq("user_id", user["id"]).execute()
            run_path.rmdir()
            raise HTTPException(status_code=409, detail="A Neural Lab training job is already running")
        _active[job_id] = cancel
    background.add_task(_run_training, credentials.credentials, user["id"], job_id, dataset_path, run_path,
                        row["config"], cancel, resume_from)
    return {"job_id": job_id, "status": "QUEUED", "estimated_parameter_count": memory.parameter_count,
            "estimated_memory_bytes": memory.estimated_total_bytes}


@router.get("/jobs")
async def list_jobs(context=USER_CONTEXT):
    user, client = context
    result = client.table("neural_lab_jobs").select(
        "id,dataset_id,config,status,error,run_path,created_at,updated_at"
    ).eq("user_id", user["id"]).order("created_at", desc=True).limit(50).execute()
    jobs = result.data or []
    run_root = (_storage(user["id"])[0] / "runs").resolve()
    for job in jobs:
        run_path = Path(job.get("run_path", "")).resolve()
        if run_path.is_relative_to(run_root):
            job_file = run_path / "job.json"
            if job_file.is_file():
                try:
                    job["metrics"] = json.loads(job_file.read_text(encoding="utf-8"))
                    job["metrics"]["checkpoints"] = [Path(path).name for path in job["metrics"].get("checkpoints", [])]
                except (OSError, json.JSONDecodeError):
                    job["metrics"] = None
                if job.get("status") in {"QUEUED", "PREPARING", "TRAINING", "VALIDATING", "CHECKPOINTING"}:
                    with _active_lock:
                        is_running_here = job["id"] in _active
                    if (not is_running_here and job.get("metrics")
                            and job["metrics"].get("state") in {"QUEUED", "PREPARING", "TRAINING", "VALIDATING", "CHECKPOINTING"}):
                        job["metrics"]["state"] = "INTERRUPTED"
                        job["status"] = "INTERRUPTED"
                        _mark_stale_job(client, user["id"], job["id"], "INTERRUPTED", "Training process stopped; resume from a saved checkpoint.")
            metrics_file = run_path / "metrics.jsonl"
            if metrics_file.is_file() and metrics_file.stat().st_size <= 1_048_576:
                try:
                    job["loss_history"] = [json.loads(line) for line in metrics_file.read_text(encoding="utf-8").splitlines()[-2000:]]
                except (OSError, json.JSONDecodeError):
                    job["loss_history"] = []
        elif job.get("status") in {"QUEUED", "PREPARING", "TRAINING", "VALIDATING", "CHECKPOINTING"}:
            with _active_lock:
                is_running_here = job["id"] in _active
            if not is_running_here:
                job["status"] = "FAILED"
                job["error"] = "Job stopped before writing a recoverable progress record. Start a new run."
                _mark_stale_job(client, user["id"], job["id"], job["status"], job["error"])
        job.pop("run_path", None)
    return {"jobs": jobs}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, context=USER_CONTEXT):
    user, client = context
    if not _ID.fullmatch(job_id):
        raise HTTPException(status_code=400, detail="Invalid job id")
    row = client.table("neural_lab_jobs").select("status").eq("id", job_id).eq("user_id", user["id"]).limit(1).execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="Job not found")
    with _active_lock:
        event = _active.get(job_id)
    if event is None:
        raise HTTPException(status_code=409, detail="Job is not running in this server process")
    event.set()
    return {"job_id": job_id, "status": "CANCELLING"}


@router.get("/models")
async def list_models(context=USER_CONTEXT):
    user, client = context
    result = client.table("neural_lab_models").select(
        "id,training_job_id,name,architecture,origin,configuration,training_status,dataset_provenance,evaluation_results,compatibility_status,created_at"
    ).eq("user_id", user["id"]).order("created_at", desc=True).execute()
    selected = client.table("neural_lab_model_selection").select("active_model_id,previous_model_id").eq("user_id", user["id"]).limit(1).execute()
    return {"models": result.data or [], "selection": selected.data[0] if selected.data else None}


def _latest_checkpoint(user_root: Path, artifact_path: str) -> Path:
    runs_root = (user_root / "runs").resolve()
    run_path = (user_root / artifact_path).resolve(strict=True)
    if not run_path.is_relative_to(runs_root):
        raise HTTPException(status_code=400, detail="Model artifact is outside approved storage")
    try:
        job = json.loads((run_path / "job.json").read_text(encoding="utf-8"))
        checkpoints = [Path(item).resolve(strict=True) for item in job.get("checkpoints", [])]
        checkpoint = checkpoints[-1]
    except (OSError, KeyError, IndexError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=404, detail="Model checkpoint is unavailable") from exc
    if not checkpoint.is_relative_to(run_path) or not checkpoint.is_file():
        raise HTTPException(status_code=400, detail="Invalid checkpoint path")
    return checkpoint


@router.post("/models", status_code=201)
async def register_model(request: RegisterModelRequest, context=USER_CONTEXT):
    from neural_lab.registry import ModelRegistry

    user, client = context
    job_result = (client.table("neural_lab_jobs").select("run_path,dataset_id,status")
                  .eq("user_id", user["id"]).eq("id", request.job_id).limit(1).execute())
    if not job_result.data:
        raise HTTPException(status_code=404, detail="Training job not found")
    job = job_result.data[0]
    existing = (client.table("neural_lab_models").select("id,name").eq("user_id", user["id"])
                .eq("training_job_id", request.job_id).limit(1).execute())
    if existing.data:
        return existing.data[0]
    user_root, _ = _storage(user["id"])
    run_path = Path(job["run_path"]).resolve()
    if not run_path.is_relative_to((user_root / "runs").resolve()):
        raise HTTPException(status_code=400, detail="Invalid training job path")
    dataset = _dataset_record(client, user["id"], job["dataset_id"])
    provenance = dataset["metadata"].get("provenance", "User-provided text")
    try:
        registered = ModelRegistry(user_root).register_completed_run(
            run_path, name=request.name, dataset_provenance=provenance,
        )
    except (OSError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    artifact_path = str(run_path.relative_to(user_root))
    row = {
        "id": registered["model_id"], "user_id": user["id"], "training_job_id": request.job_id,
        "name": registered["name"],
        "architecture": registered["architecture"], "origin": registered["origin"],
        "configuration": registered["configuration"], "training_status": registered["training_status"],
        "artifact_path": artifact_path, "dataset_provenance": provenance,
        "evaluation_results": {}, "compatibility_status": registered["compatibility_status"],
    }
    try:
        client.table("neural_lab_models").insert(row).execute()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="The model could not be persisted") from exc
    return {key: value for key, value in row.items() if key not in {"user_id", "artifact_path"}}


@router.post("/models/{model_id}/evaluate")
async def evaluate_model(model_id: str, request: EvaluateRequest, context=USER_CONTEXT):
    from neural_lab.evaluation import evaluate_checkpoint

    user, client = context
    if not _ID.fullmatch(model_id):
        raise HTTPException(status_code=400, detail="Invalid model id")
    model_result = (client.table("neural_lab_models").select("artifact_path,evaluation_results")
                    .eq("user_id", user["id"]).eq("id", model_id).limit(1).execute())
    if not model_result.data:
        raise HTTPException(status_code=404, detail="Model not found")
    dataset = _dataset_record(client, user["id"], request.dataset_id)
    _, store = _storage(user["id"])
    checkpoint = _latest_checkpoint(_storage(user["id"])[0], model_result.data[0]["artifact_path"])
    try:
        measured = await asyncio.to_thread(
            evaluate_checkpoint, checkpoint, store.get_path(dataset["digest"]), max_batches=request.max_batches,
        )
    except (OSError, ValueError, FloatingPointError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    results = model_result.data[0].get("evaluation_results") or {}
    results[request.dataset_id] = measured
    client.table("neural_lab_models").update({"evaluation_results": results}).eq("user_id", user["id"]).eq("id", model_id).execute()
    return measured


@router.post("/models/{model_id}/select")
async def select_model(model_id: str, context=USER_CONTEXT):
    from neural_lab.registry import ModelRegistry

    user, client = context
    if not _ID.fullmatch(model_id):
        raise HTTPException(status_code=400, detail="Invalid model id")
    model = (client.table("neural_lab_models").select("id").eq("user_id", user["id"])
             .eq("id", model_id).limit(1).execute())
    if not model.data:
        raise HTTPException(status_code=404, detail="Model not found")
    selection = (client.table("neural_lab_model_selection").select("active_model_id")
                 .eq("user_id", user["id"]).limit(1).execute())
    previous = selection.data[0]["active_model_id"] if selection.data else None
    client.table("neural_lab_model_selection").upsert(
        {"user_id": user["id"], "active_model_id": model_id, "previous_model_id": previous},
        on_conflict="user_id",
    ).execute()
    ModelRegistry(_storage(user["id"])[0]).select_experimental(model_id)
    return {"active_model_id": model_id, "previous_model_id": previous,
            "compatibility_status": "experimental-only; not connected to Astrovox chat"}


@router.post("/models/rollback")
async def rollback_model(context=USER_CONTEXT):
    from neural_lab.registry import ModelRegistry

    user, client = context
    selection = (client.table("neural_lab_model_selection").select("active_model_id,previous_model_id")
                 .eq("user_id", user["id"]).limit(1).execute())
    if not selection.data or not selection.data[0]["previous_model_id"]:
        raise HTTPException(status_code=409, detail="No previous experimental model is available")
    current = selection.data[0]
    client.table("neural_lab_model_selection").update(
        {"active_model_id": current["previous_model_id"], "previous_model_id": None}
    ).eq("user_id", user["id"]).execute()
    ModelRegistry(_storage(user["id"])[0]).rollback_experimental_selection()
    return {"active_model_id": current["previous_model_id"], "previous_model_id": None}


@router.post("/generate")
async def generate_experimental(request: GenerateRequest, context=USER_CONTEXT):
    from neural_lab.evaluation import generate_text

    user, client = context
    selection = (client.table("neural_lab_model_selection").select("active_model_id")
                 .eq("user_id", user["id"]).limit(1).execute())
    if not selection.data or not selection.data[0]["active_model_id"]:
        raise HTTPException(status_code=409, detail="Select a registered experimental model first")
    model = (client.table("neural_lab_models").select("artifact_path").eq("user_id", user["id"])
             .eq("id", selection.data[0]["active_model_id"]).limit(1).execute())
    if not model.data:
        raise HTTPException(status_code=404, detail="Selected model is unavailable")
    checkpoint = _latest_checkpoint(_storage(user["id"])[0], model.data[0]["artifact_path"])
    try:
        output = await asyncio.to_thread(
            generate_text, checkpoint, request.prompt, max_new_tokens=request.max_new_tokens,
            temperature=request.temperature, top_k=request.top_k,
        )
    except (OSError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"text": output, "model_id": selection.data[0]["active_model_id"], "mode": "experimental"}
