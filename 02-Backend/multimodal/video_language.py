import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple


@dataclass
class VideoFeatures:
    frames: List[np.ndarray]
    temporal_features: np.ndarray
    optical_flow: Optional[np.ndarray]
    fps: float
    duration: float


class VideoLanguageModel:
    def __init__(self, fps: float = 8.0, feature_dim: int = 128):
        self.fps = fps
        self.feature_dim = feature_dim
        self._rng = np.random.default_rng(42)

    def extract_frames(self, video_frames: List[np.ndarray], frame_rate: float) -> List[np.ndarray]:
        if frame_rate <= self.fps:
            return video_frames
        stride = int(frame_rate / self.fps)
        sampled = []
        for i in range(0, len(video_frames), stride):
            sampled.append(video_frames[i])
        return sampled

    def compute_temporal_features(self, frames: List[np.ndarray]) -> np.ndarray:
        if len(frames) == 0:
            return np.zeros(self.feature_dim)
        frame_vectors = [self._frame_to_vector(f) for f in frames]
        frame_matrix = np.array(frame_vectors)
        temporal = np.mean(frame_matrix, axis=0)
        if len(frames) > 1:
            diffs = np.diff(frame_matrix, axis=0)
            temporal = np.concatenate([temporal, np.mean(diffs, axis=0)])
        temporal = temporal[: self.feature_dim]
        if len(temporal) < self.feature_dim:
            temporal = np.pad(temporal, (0, self.feature_dim - len(temporal)))
        return temporal / (np.linalg.norm(temporal) + 1e-8)

    def _frame_to_vector(self, frame: np.ndarray) -> np.ndarray:
        if frame.ndim == 3:
            gray = frame.mean(axis=2)
        else:
            gray = frame
        h, w = gray.shape
        vec = []
        for i in range(4):
            for j in range(4):
                y1, x1 = i * h // 4, j * w // 4
                y2, x2 = (i + 1) * h // 4, (j + 1) * w // 4
                block = gray[y1:y2, x1:x2]
                vec.extend([block.mean(), block.std()])
        return np.array(vec[:32], dtype=np.float64)

    def estimate_optical_flow(self, prev_frame: np.ndarray, curr_frame: np.ndarray) -> np.ndarray:
        if prev_frame.shape != curr_frame.shape:
            curr_frame = self._resize_frame(curr_frame, prev_frame.shape)
        prev_gray = prev_frame.mean(axis=2) if prev_frame.ndim == 3 else prev_frame
        curr_gray = curr_frame.mean(axis=2) if curr_frame.ndim == 3 else curr_frame
        h, w = prev_gray.shape
        flow = np.zeros((h, w, 2), dtype=np.float64)
        for y in range(0, h, 8):
            for x in range(0, w, 8):
                patch_h, patch_w = min(8, h - y), min(8, w - x)
                prev_patch = prev_gray[y:y + patch_h, x:x + patch_w]
                curr_patch = curr_gray[y:y + patch_h, x:x + patch_w]
                best_dx, best_dy = self._block_match(prev_patch, curr_patch)
                flow[y:y + patch_h, x:x + patch_w, 0] = best_dx
                flow[y:y + patch_h, x:x + patch_w, 1] = best_dy
        return flow

    def _block_match(self, prev_patch: np.ndarray, curr_patch: np.ndarray, search_range: int = 5) -> Tuple[int, int]:
        best_dx, best_dy = 0, 0
        best_score = float("inf")
        for dy in range(-search_range, search_range + 1):
            for dx in range(-search_range, search_range + 1):
                shifted = np.roll(np.roll(curr_patch, dy, axis=0), dx, axis=1)
                diff = np.mean((prev_patch - shifted) ** 2)
                if diff < best_score:
                    best_score = diff
                    best_dx, best_dy = dx, dy
        return best_dx, best_dy

    def _resize_frame(self, frame: np.ndarray, target_shape: Tuple[int, int]) -> np.ndarray:
        from scipy.ndimage import zoom
        h, w = frame.shape[:2]
        th, tw = target_shape[:2]
        if frame.ndim == 3:
            return np.array([zoom(frame[:, :, c], (th / h, tw / w)) for c in range(3)]).transpose(1, 2, 0)
        return zoom(frame, (th / h, tw / w))

    def understand_video(self, frames: List[np.ndarray], frame_rate: float, question: str) -> Dict[str, Any]:
        sampled = self.extract_frames(frames, frame_rate)
        temporal_features = self.compute_temporal_features(sampled)
        optical_flow = None
        if len(sampled) >= 2:
            flow_maps = []
            for i in range(len(sampled) - 1):
                flow = self.estimate_optical_flow(sampled[i], sampled[i + 1])
                flow_maps.append(flow)
            optical_flow = np.array(flow_maps)
        duration = len(frames) / frame_rate
        video_features = VideoFeatures(
            frames=sampled,
            temporal_features=temporal_features,
            optical_flow=optical_flow,
            fps=self.fps,
            duration=duration,
        )
        answer = self._temporal_reasoning(video_features, question)
        return {
            "answer": answer,
            "temporal_features": temporal_features.tolist(),
            "num_sampled_frames": len(sampled),
            "duration": duration,
        }

    def _temporal_reasoning(self, video_features: VideoFeatures, question: str) -> str:
        q_lower = question.lower()
        motion = 0.0
        if video_features.optical_flow is not None:
            motion = np.mean(np.abs(video_features.optical_flow))
        if "action" in q_lower or "happening" in q_lower:
            if motion > 2.0:
                return "The video shows significant motion and action."
            return "The video shows minimal motion."
        if "how long" in q_lower:
            return f"The video duration is {video_features.duration:.2f} seconds."
        if "how many frames" in q_lower:
            return f"There are {len(video_features.frames)} sampled frames."
        if "motion" in q_lower:
            return f"The average motion magnitude is {motion:.2f} pixels per frame."
        return f"The video contains {len(video_features.frames)} frames with motion intensity {motion:.2f}."

    def summarize_video(self, video_features: VideoFeatures) -> str:
        motion = 0.0
        if video_features.optical_flow is not None:
            motion = np.mean(np.abs(video_features.optical_flow))
        if motion > 3.0:
            return "High-motion video with dynamic content."
        if motion > 1.0:
            return "Moderate-motion video."
        return "Low-motion or static video content."
