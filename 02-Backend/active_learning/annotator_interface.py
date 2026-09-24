from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class AnnotationStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class AnnotatorInterface:
    def __init__(self, annotator_id: str):
        self.annotator_id = annotator_id
        self._annotations: Dict[int, Dict[str, Any]] = {}

    def submit_annotation(
        self, sample_id: int, label: Any, confidence: float = 1.0
    ) -> None:
        self._annotations[sample_id] = {
            "label": label,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat(),
            "annotator_id": self.annotator_id,
            "status": AnnotationStatus.COMPLETED.value,
        }

    def skip(self, sample_id: int) -> None:
        self._annotations[sample_id] = {
            "label": None,
            "confidence": 0.0,
            "timestamp": datetime.utcnow().isoformat(),
            "annotator_id": self.annotator_id,
            "status": AnnotationStatus.SKIPPED.value,
        }

    def get_annotation(self, sample_id: int) -> Optional[Dict[str, Any]]:
        return self._annotations.get(sample_id)

    def get_all_annotations(self) -> Dict[int, Dict[str, Any]]:
        return dict(self._annotations)

    def completed_count(self) -> int:
        return sum(
            1
            for a in self._annotations.values()
            if a["status"] == AnnotationStatus.COMPLETED.value
        )

    def skipped_count(self) -> int:
        return sum(
            1
            for a in self._annotations.values()
            if a["status"] == AnnotationStatus.SKIPPED.value
        )

    def pending_count(self) -> int:
        return sum(
            1
            for a in self._annotations.values()
            if a["status"] == AnnotationStatus.PENDING.value
        )

    def total_annotated(self) -> int:
        return self.completed_count() + self.skipped_count()

    def average_confidence(self) -> float:
        completed = [
            a["confidence"]
            for a in self._annotations.values()
            if a["status"] == AnnotationStatus.COMPLETED.value
        ]
        if not completed:
            return 0.0
        return sum(completed) / len(completed)
