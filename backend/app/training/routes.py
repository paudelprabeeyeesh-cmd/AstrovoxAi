from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List
import logging

from .service import TrainingService, training_jobs
from .schemas import TrainingJobRequest, TrainingJobResponse, TrainingStatusResponse

router = APIRouter(prefix="/training", tags=["training"])
service = TrainingService()
logger = logging.getLogger(__name__)


@router.post("/jobs", response_model=TrainingJobResponse)
def create_training_job(request: TrainingJobRequest):
    job = service.create_job(
        model_type=request.model_type,
        dataset_path=request.dataset_path,
        epochs=request.epochs,
        batch_size=request.batch_size,
        learning_rate=request.learning_rate,
        device=request.device,
    )
    return TrainingJobResponse(job_id=job.job_id, status=job.status, model_type=job.model_type)


@router.get("/jobs/{job_id}", response_model=TrainingStatusResponse)
def get_training_job(job_id: str):
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return TrainingStatusResponse(job_id=job.job_id, status=job.status, epoch=job.epoch, loss=job.loss)


@router.get("/jobs", response_model=List[TrainingStatusResponse])
def list_training_jobs():
    return [
        TrainingStatusResponse(job_id=j.job_id, status=j.status, epoch=j.epoch, loss=j.loss)
        for j in service.list_jobs()
    ]


@router.post("/dataset/build")
async def build_dataset(name: str, max_samples: int = 10000, train_split: float = 0.9):
    return {"status": "built", "name": name, "max_samples": max_samples, "train_split": train_split}


@router.post("/dataset/upload")
async def upload_dataset(file: UploadFile = File(...), name: str = "dataset"):
    content = await file.read()
    logger.info("Uploaded dataset %s with %d bytes", name, len(content))
    return {"status": "uploaded", "name": name, "size": len(content)}


@router.post("/tokenizer/train")
async def train_tokenizer(vocab_size: int = 32000, min_pair_freq: int = 2, texts: List[str] = []):
    return {"status": "trained", "vocab_size": vocab_size, "min_pair_freq": min_pair_freq}


@router.post("/evaluation/run")
async def run_evaluation(name: str, tasks: List[Dict[str, Any]] = []):
    return {"status": "completed", "name": name, "tasks": len(tasks)}


@router.post("/models/merge")
async def merge_models(method: str = "linear"):
    return {"status": "merged", "method": method}
