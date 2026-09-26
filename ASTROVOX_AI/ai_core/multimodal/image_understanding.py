from typing import Optional, List
from PIL import Image
import torch


class ImageUnderstanding:
    def __init__(self, model_name: str = 'clip', device: str = 'cuda'):
        self.model_name = model_name
        self.device = device
        self.model = None
        self.processor = None
        if model_name == 'clip':
            try:
                from transformers import CLIPProcessor, CLIPModel
                self.model = CLIPModel.from_pretrained('openai/clip-vit-base-patch32')
                self.processor = CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32')
                self.model.to(device)
            except ImportError:
                logger.warning("transformers not installed, image understanding unavailable")

    def encode_image(self, image_path: str) -> Optional[torch.Tensor]:
        if self.model is None:
            return None
        image = Image.open(image_path).convert('RGB')
        inputs = self.processor(images=image, return_tensors='pt').to(self.device)
        with torch.no_grad():
            outputs = self.model.get_image_features(**inputs)
        return outputs

    def classify(self, image_path: str, labels: List[str]) -> List[Tuple[str, float]]:
        image_emb = self.encode_image(image_path)
        if image_emb is None or self.model is None:
            return []
        text_inputs = self.processor(text=labels, return_tensors='pt', padding=True).to(self.device)
        with torch.no_grad():
            text_embs = self.model.get_text_features(**text_inputs)
        scores = (image_emb @ text_embs.T).softmax(dim=-1).squeeze(0)
        return sorted(zip(labels, scores.cpu().tolist()), key=lambda x: x[1], reverse=True)

    def similarity(self, image_path: str, text: str) -> float:
        image_emb = self.encode_image(image_path)
        if image_emb is None or self.model is None:
            return 0.0
        text_inputs = self.processor(text=[text], return_tensors='pt').to(self.device)
        with torch.no_grad():
            text_emb = self.model.get_text_features(**text_inputs)
        return (image_emb @ text_emb.T).item()
