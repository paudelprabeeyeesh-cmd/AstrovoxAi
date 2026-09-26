import os
import base64
import json
import logging
from typing import Any

import numpy as np

from ..config import settings
from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)


class CrossModalRetriever:
    def __init__(self):
        self._text_model = os.getenv("TEXT_EMBEDDING_MODEL", "text-embedding-3-small")
        self._image_model = os.getenv("IMAGE_EMBEDDING_MODEL", "clip-vit-base-patch32")
        self._audio_model = os.getenv("AUDIO_EMBEDDING_MODEL", "whisper-1")
        self._vector_dim = int(os.getenv("VECTOR_DIM", "1536"))

    def embed_text(self, text: str) -> list[float]:
        try:
            import openai
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.embeddings.create(input=text, model=self._text_model)
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Text embedding failed: {e}")
            return self._fallback_embed(text)

    def embed_image(self, image: str) -> list[float]:
        try:
            if image.startswith("data:"):
                image = image.split(",", 1)[1]
            image_bytes = base64.b64decode(image)
            import io
            from PIL import Image
            img = Image.open(io.BytesIO(image_bytes))
            img = img.convert("RGB").resize((224, 224))
            arr = np.array(img, dtype=np.float32) / 255.0
            vec = arr.mean(axis=(0, 1)).tolist()
            return self._pad_vector(vec)
        except Exception as e:
            logger.error(f"Image embedding failed: {e}")
            return self._fallback_embed("image")

    def embed_audio(self, audio: str) -> list[float]:
        try:
            if audio.startswith("data:"):
                audio = audio.split(",", 1)[1]
            audio_bytes = base64.b64decode(audio)
            import io
            from pydub import AudioSegment
            segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
            samples = np.array(segment.get_array_of_samples(), dtype=np.float32)
            if len(samples) == 0:
                return self._fallback_embed("audio")
            mfcc_like = [
                float(samples.mean()),
                float(samples.std()),
                float(samples.max()),
                float(samples.min()),
            ]
            return self._pad_vector(mfcc_like)
        except Exception as e:
            logger.error(f"Audio embedding failed: {e}")
            return self._fallback_embed("audio")

    def search_cross_modal(self, query: str, modality: str = "text", limit: int = 10) -> list[dict[str, Any]]:
        query_vec = self.embed_text(query) if modality == "text" else self.embed_text(query)
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, content, embedding, metadata, source_modality FROM multimodal_embeddings ORDER BY embedding <=> ?::vector LIMIT ?",
                (str(query_vec), limit),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "content": r["content"],
                    "score": 1.0 - float(r["embedding"]),
                    "metadata": json.loads(r["metadata"]) if r["metadata"] else {},
                    "modality": r.get("source_modality", modality),
                }
                for r in rows
            ]

    def _fallback_embed(self, text: str) -> list[float]:
        vec = [hash(c) % 1000 / 1000.0 for c in text[: self._vector_dim]]
        return self._pad_vector(vec)

    def _pad_vector(self, vec: list[float]) -> list[float]:
        while len(vec) < self._vector_dim:
            vec.append(0.0)
        return vec[: self._vector_dim]
