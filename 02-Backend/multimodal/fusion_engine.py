import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from multimodal.cross_modal_attention import ModalityFusion, ModalityAlignment


@dataclass
class FusionResult:
    fused_embedding: np.ndarray
    alignment_scores: Dict[str, float]
    modality_contributions: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)


class FusionEngine:
    def __init__(self, embed_dim: int = 256):
        self.embed_dim = embed_dim
        self.fusion = ModalityFusion(embed_dim=embed_dim)
        self.alignment = ModalityAlignment(embed_dim=embed_dim)

    def fuse(
        self,
        text_emb: np.ndarray,
        image_emb: np.ndarray,
        audio_emb: Optional[np.ndarray] = None,
    ) -> FusionResult:
        early = self.fusion.early_fusion(text_emb, image_emb, audio_emb)
        late = self.fusion.late_fusion(text_emb, image_emb, audio_emb)
        hybrid = self.fusion.hybrid_fusion(text_emb, image_emb, audio_emb)

        embeddings: Dict[str, np.ndarray] = {
            "text": text_emb,
            "image": image_emb,
            "early": early,
            "late": late,
        }
        if audio_emb is not None:
            embeddings["audio"] = audio_emb

        aligned = self.alignment.align_modalities(embeddings)
        alignment_scores = {k: float(v[0]) for k, v in aligned.items()}

        contributions = {
            "text": float(np.linalg.norm(text_emb)),
            "image": float(np.linalg.norm(image_emb)),
        }
        if audio_emb is not None:
            contributions["audio"] = float(np.linalg.norm(audio_emb))

        return FusionResult(
            fused_embedding=hybrid,
            alignment_scores=alignment_scores,
            modality_contributions=contributions,
        )
