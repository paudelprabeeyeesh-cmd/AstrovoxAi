from typing import Optional, Dict, Any, List
import cv2
import numpy as np


class VideoCaptionExtractor:
    def __init__(self, frame_interval: int = 30, model_name: str = 'blip'):
        self.frame_interval = frame_interval
        self.model_name = model_name
        self.model = None
        if model_name == 'blip':
            try:
                from transformers import BlipProcessor, BlipForConditionalGeneration
                self.processor = BlipProcessor.from_pretrained('Salesforce/blip-image-captioning-base')
                self.model = BlipForConditionalGeneration.from_pretrained('Salesforce/blip-image-captioning-base')
            except ImportError:
                pass

    def extract_frames(self, video_path: str) -> List[np.ndarray]:
        cap = cv2.VideoCapture(video_path)
        frames = []
        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if frame_count % self.frame_interval == 0:
                frames.append(frame)
            frame_count += 1
        cap.release()
        return frames

    def caption_frame(self, frame: np.ndarray) -> str:
        if self.model is None:
            return 'Model not available'
        from PIL import Image
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        inputs = self.processor(image, return_tensors='pt')
        out = self.model.generate(**inputs)
        return self.processor.decode(out[0], skip_special_tokens=True)

    def caption_video(self, video_path: str) -> List[Dict[str, Any]]:
        frames = self.extract_frames(video_path)
        captions = []
        for i, frame in enumerate(frames):
            caption = self.caption_frame(frame)
            captions.append({'frame': i * self.frame_interval, 'caption': caption})
        return captions
