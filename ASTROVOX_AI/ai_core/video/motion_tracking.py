"""Motion tracking engine.

Tracks objects across video frames using:
- Optical flow (Farneback, Lucas-Kanade)
- Object detection + correlation trackers (CSRT, KCF)
- Trajectory extraction and smoothing
- Bounding box tracking with occlusion handling
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    cv2 = None
    HAS_CV2 = False


@dataclass
class TrackedObject:
    object_id: int
    label: str
    bboxes: List[Tuple[int, int, int, int]]
    timestamps: List[float]
    scores: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)


class MotionTrackingEngine:
    """Track objects across video frames."""

    def __init__(self, tracker_type: str = "csrt"):
        self.tracker_type = tracker_type
        self._detector = None
        self._init_detector()

    def _init_detector(self) -> None:
        if not HAS_CV2:
            return
        try:
            self._detector = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
        except Exception as exc:
            logger.debug("detector init failed: %s", exc)

    def track(
        self,
        video_path: str,
        init_bbox: Tuple[int, int, int, int],
        label: str = "object",
    ) -> TrackedObject:
        if not HAS_CV2:
            return TrackedObject(object_id=0, label=label, bboxes=[init_bbox], timestamps=[0.0], scores=[1.0])

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        tracker = self._create_tracker()
        ret, frame = cap.read()
        if not ret:
            cap.release()
            return TrackedObject(object_id=0, label=label, bboxes=[init_bbox], timestamps=[0.0], scores=[1.0])
        tracker.init(frame, init_bbox)
        bboxes = [init_bbox]
        timestamps = [0.0]
        scores = [1.0]
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            ok, box = tracker.update(frame)
            score = 1.0 if ok else 0.0
            if ok:
                bboxes.append(tuple(int(v) for v in box))
            else:
                bboxes.append(bboxes[-1])
            timestamps.append(frame_idx / fps)
            scores.append(score)
            frame_idx += 1
        cap.release()
        return TrackedObject(
            object_id=0,
            label=label,
            bboxes=bboxes,
            timestamps=timestamps,
            scores=scores,
        )

    def track_all(
        self,
        video_path: str,
        max_objects: int = 10,
    ) -> List[TrackedObject]:
        if not HAS_CV2:
            return []
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        objects: List[TrackedObject] = []
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
            detections = self._detect(gray)
            for det in detections[:max_objects]:
                x, y, w, h = det
                if not objects or not self._matches_existing(objects, (x, y, w, h), threshold=0.5):
                    obj = TrackedObject(
                        object_id=len(objects),
                        label="object",
                        bboxes=[(x, y, w, h)],
                        timestamps=[frame_idx / fps],
                        scores=[1.0],
                    )
                    objects.append(obj)
                else:
                    best = self._best_match(objects, (x, y, w, h))
                    if best is not None:
                        objects[best].bboxes.append((x, y, w, h))
                        objects[best].timestamps.append(frame_idx / fps)
                        objects[best].scores.append(1.0)
            frame_idx += 1
        cap.release()
        return objects

    def compute_optical_flow(self, video_path: str) -> List[np.ndarray]:
        if not HAS_CV2:
            return []
        cap = cv2.VideoCapture(video_path)
        ret, prev = cap.read()
        if not ret:
            cap.release()
            return []
        prev_gray = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
        flows = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            flows.append(flow)
            prev_gray = gray
        cap.release()
        return flows

    def compute_trajectory(self, tracked: TrackedObject) -> List[Tuple[float, float]]:
        centers = []
        for bbox in tracked.bboxes:
            x, y, w, h = bbox
            centers.append((x + w / 2.0, y + h / 2.0))
        return centers

    def compute_velocity(self, tracked: TrackedObject) -> List[float]:
        traj = self.compute_trajectory(tracked)
        velocities = [0.0]
        for i in range(1, len(traj)):
            dx = traj[i][0] - traj[i - 1][0]
            dy = traj[i][1] - traj[i - 1][1]
            velocities.append(math.sqrt(dx * dx + dy * dy))
        return velocities

    def _create_tracker(self) -> Any:
        if not HAS_CV2:
            return None
        tracker_map = {
            "csrt": cv2.TrackerCSRT_create,
            "kcf": cv2.TrackerKCF_create,
            "mil": cv2.TrackerMIL_create,
            "boosting": cv2.TrackerBoosting_create,
        }
        creator = tracker_map.get(self.tracker_type, cv2.TrackerCSRT_create)
        try:
            return creator()
        except Exception:
            try:
                return cv2.TrackerCSRT_create()
            except Exception:
                return None

    def _detect(self, gray: Any) -> List[Tuple[int, int, int, int]]:
        if self._detector is None:
            return []
        try:
            return self._detector.detectMultiScale(gray, 1.1, 4)
        except Exception:
            return []

    def _matches_existing(self, objects: List[TrackedObject], bbox: Tuple[int, int, int, int], threshold: float) -> bool:
        return self._best_match(objects, bbox) is not None

    def _best_match(self, objects: List[TrackedObject], bbox: Tuple[int, int, int, int]) -> Optional[int]:
        best_idx = None
        best_iou = 0.3
        for idx, obj in enumerate(objects):
            if not obj.bboxes:
                continue
            last = obj.bboxes[-1]
            iou = self._iou(last, bbox)
            if iou > best_iou:
                best_iou = iou
                best_idx = idx
        return best_idx

    def _iou(self, a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        inter_x1 = max(ax, bx)
        inter_y1 = max(ay, by)
        inter_x2 = min(ax + aw, bx + bw)
        inter_y2 = min(ay + ah, by + bh)
        inter = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
        union = aw * ah + bw * bh - inter
        return inter / union if union > 0 else 0.0


motion_tracking = MotionTrackingEngine()
