from fastapi import APIRouter, HTTPException
from typing import List

from .service import TrainingService, training_jobs
from .schemas import TrainingJobRequest, TrainingJobResponse, TrainingStatusResponse

router = APIRouter(prefix="/training", tags=["training"])
service = TrainingService()


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
