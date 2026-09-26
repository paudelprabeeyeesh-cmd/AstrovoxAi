"""
Training API endpoints.
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.training.dataset_builder import DatasetBuilder, DatasetManifest
from app.training.evaluation import EvaluationPipeline, EvalTask
from app.training.merging import ModelMerger
from app.training.tokenizer_trainer import TokenizerTrainer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training", tags=["training"])


class TrainTokenizerRequest(BaseModel):
    vocab_size: int = 32000
    min_pair_freq: int = 2
    texts: Optional[List[str]] = None


class BuildDatasetRequest(BaseModel):
    name: str
    max_samples: int = 10000
    train_split: float = 0.9


class EvaluationRequest(BaseModel):
    name: str
    tasks: List[Dict[str, Any]]


class MergeModelsRequest(BaseModel):
    method: str = "linear"
    weights: Optional[List[float]] = None


@router.post("/tokenizer/train")
async def train_tokenizer(request: TrainTokenizerRequest):
    trainer = TokenizerTrainer(vocab_size=request.vocab_size, min_pair_freq=request.min_pair_freq)
    texts = request.texts or ["sample text for tokenizer training"]
    tokenizer = trainer.train(texts)
    metrics = trainer.evaluate(tokenizer, texts)
    return {"status": "ok", "vocab_size": metrics["vocab_size"], "compression_ratio": metrics["compression_ratio"]}


@router.post("/dataset/build")
async def build_dataset(request: BuildDatasetRequest):
    builder = DatasetBuilder(name=request.name, max_samples=request.max_samples)
    train, val = builder.build(train_split=request.train_split)
    return {
        "status": "ok",
        "name": request.name,
        "train_samples": len(train.samples),
        "val_samples": len(val.samples),
        "train_hash": train.hash,
        "val_hash": val.hash,
    }


@router.post("/dataset/upload")
async def upload_dataset(file: UploadFile = File(...), name: str = Form(...)):
    fd, path = tempfile.mkstemp(suffix=".jsonl", prefix=f"dataset_{name}_")
    os.close(fd)
    with open(path, "wb") as f:
        f.write(await file.read())
    builder = DatasetBuilder(name=name)
    count = builder.add_from_file(path)
    train, val = builder.build()
    return {"status": "ok", "name": name, "imported": count, "train_samples": len(train.samples), "val_samples": len(val.samples)}


@router.post("/evaluation/run")
async def run_evaluation(request: EvaluationRequest):
    pipeline = EvaluationPipeline(name=request.name)
    pipeline.register_tasks([EvalTask(**t) for t in request.tasks])
    result = pipeline.run(lambda prompt: f"Response to: {prompt}")
    return result


@router.post("/models/merge")
async def merge_models(request: MergeModelsRequest):
    return {"status": "ok", "method": request.method, "message": "Model merge endpoint ready"}


@router.get("/health")
async def training_health():
    return {"status": "ok", "module": "training"}
