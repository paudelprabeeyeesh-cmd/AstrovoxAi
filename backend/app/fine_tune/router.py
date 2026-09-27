"""FastAPI router for fine-tuning endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .service import fine_tune_service

router = APIRouter(prefix="/fine-tune", tags=["fine-tune"])


class FineTuneJobRequest(BaseModel):
    model_name: str = Field(default="default")
    use_lora: bool = Field(default=True)
    use_qlora: bool = Field(default=False)
    lora_rank: int = Field(default=8, ge=1)
    lr: float = Field(default=1e-4, gt=0)
    batch_size: int = Field(default=8, ge=1)
    num_epochs: int = Field(default=3, ge=1)


class LoRAInjectRequest(BaseModel):
    model_name: str = Field(default="default")
    lora_rank: int = Field(default=8, ge=1)
    lora_alpha: float = Field(default=16.0, gt=0)


class QLoRAPrepareRequest(BaseModel):
    model_name: str = Field(default="default")
    qlora_bits: int = Field(default=4, ge=1, le=8)
    lora_rank: int = Field(default=8, ge=1)


class DPOTrainRequest(BaseModel):
    model_name: str = Field(default="default")
    beta: float = Field(default=0.1, ge=0)
    lr: float = Field(default=1e-5, gt=0)


class RLHFTrainRequest(BaseModel):
    model_name: str = Field(default="default")
    kl_coef: float = Field(default=0.1, ge=0)
    lr: float = Field(default=1e-5, gt=0)


@router.post("/jobs")
async def create_fine_tune_job(request: FineTuneJobRequest):
    job = fine_tune_service.create_job(
        model_name=request.model_name,
        use_lora=request.use_lora,
        use_qlora=request.use_qlora,
        lora_rank=request.lora_rank,
        lr=request.lr,
        batch_size=request.batch_size,
        num_epochs=request.num_epochs,
    )
    return job


@router.post("/lora/inject")
async def inject_lora(request: LoRAInjectRequest):
    result = fine_tune_service.inject_lora(
        model_name=request.model_name,
        lora_rank=request.lora_rank,
        lora_alpha=request.lora_alpha,
    )
    return result


@router.post("/qlora/prepare")
async def prepare_qlora(request: QLoRAPrepareRequest):
    result = fine_tune_service.prepare_qlora(
        model_name=request.model_name,
        qlora_bits=request.qlora_bits,
        lora_rank=request.lora_rank,
    )
    return result


@router.post("/dpo/train")
async def dpo_train(request: DPOTrainRequest):
    result = fine_tune_service.dpo_train(
        model_name=request.model_name,
        beta=request.beta,
        lr=request.lr,
    )
    return result


@router.post("/rlhf/train")
async def rlhf_train(request: RLHFTrainRequest):
    result = fine_tune_service.rlhf_train(
        model_name=request.model_name,
        kl_coef=request.kl_coef,
        lr=request.lr,
    )
    return result
