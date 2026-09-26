from typing import Dict, Any, List
import cv2
import numpy as np
from ASTROVOX_AI.ai_core.multimodal.image_understanding import ImageUnderstanding


class VideoUnderstanding:
    def __init__(self, frame_interval: int = 10, device: str = 'cuda'):
        self.frame_interval = frame_interval
        self.image_understanding = ImageUnderstanding(device=device)

    def extract_frames(self, video_path: str, max_frames: int = 100) -> List[np.ndarray]:
        cap = cv2.VideoCapture(video_path)
        frames = []
        frame_count = 0
        while cap.isOpened() and len(frames) < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_count % self.frame_interval == 0:
                frames.append(frame)
            frame_count += 1
        cap.release()
        return frames

    def analyze_video(self, video_path: str, query: str = '') -> Dict[str, Any]:
        frames = self.extract_frames(video_path)
        frame_analyses = []
        for i, frame in enumerate(frames):
            temp_path = f'temp_frame_{i}.jpg'
            cv2.imwrite(temp_path, frame)
            analysis = self.image_understanding.classify(temp_path, ['person', 'car', 'animal', 'building', 'nature'])
            frame_analyses.append({'frame': i, 'analysis': analysis, 'query_score': self.image_understanding.similarity(temp_path, query) if query else 0.0})
        frame_analyses.sort(key=lambda x: x.get('query_score', 0), reverse=True)
        return {'video_path': video_path, 'frames_analyzed': len(frames), 'top_frames': frame_analyses[:5]}

    def detect_scenes(self, video_path: str, threshold: float = 0.3) -> List[int]:
        cap = cv2.VideoCapture(video_path)
        prev_frame = None
        scene_changes = []
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev_frame is not None:
                diff = np.mean(np.abs(gray.astype(float) - prev_frame.astype(float)))
                if diff > threshold * 255:
                    scene_changes.append(frame_idx)
            prev_frame = gray
            frame_idx += 1
        cap.release()
        return scene_changes
