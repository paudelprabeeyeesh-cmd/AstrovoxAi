"""Edge AI."""
from .inference import AIEdgeInference, AIEdgeModel
from .compression import AIModelCompression, AICompressedModel

__all__ = [
    "AIEdgeInference",
    "AIEdgeModel",
    "AIModelCompression",
    "AICompressedModel",
]
