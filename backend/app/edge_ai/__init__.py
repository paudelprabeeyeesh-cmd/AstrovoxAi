"""Edge AI package initialization."""
from .edge_inference import EdgeInference, EdgeModel
from .model_compression import ModelCompressor, CompressedModel
from .sync import EdgeSync, SyncQueue

__all__ = [
    "EdgeInference",
    "EdgeModel",
    "ModelCompressor",
    "CompressedModel",
    "EdgeSync",
    "SyncQueue",
]
