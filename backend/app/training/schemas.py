from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class TrainingJobRequest(BaseModel):
    model_type: str
    dataset_path: str
    epochs: int = 1
    batch_size: int = 4
    learning_rate: float = 1e-4
    device: str = "cpu"


class TrainingJobResponse(BaseModel):
    job_id: str
    status: str
    model_type: str


class TrainingStatusResponse(BaseModel):
    job_id: str
    status: str
    epoch: int
    loss: Optional[float] = None
