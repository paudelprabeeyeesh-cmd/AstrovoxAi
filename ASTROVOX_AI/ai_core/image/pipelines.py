import os
import io
import base64
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ImageResult:
    success: bool
    data: bytes
    mime_type: str
    metadata: Dict[str, Any]
    error: Optional[str] = None


class ImageAIPipelines:
    def __init__(self, device: str = "cpu"):
        self.device = device
        self._txt2img_pipe = None
        self._img2img_pipe = None
        self._inpaint_pipe = None
        self._clip_model = None
        self._clip_processor = None
        self._ocr_reader = None
        self._detr_model = None
        self._detr_processor = None
        self._segformer_model = None
        self._segformer_processor = None

    def _ensure_dirs(self) -> Path:
        base = Path(os.getenv("ASTROVOX_IMAGE_DIR", "/tmp/astrovox_images"))
        base.mkdir(parents=True, exist_ok=True)
        return base

    def _load_diffusion(self, model_id: str, task: str):
        try:
            from diffusers import DiffusionPipeline
            import torch
            pipe = DiffusionPipeline.from_pretrained(
                model_id,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            )
            pipe = pipe.to(self.device)
            if self.device == "cuda":
                pipe.enable_attention_slicing()
            return pipe
        except Exception as e:
            logger.error(f"Failed to load diffusion model {model_id}: {e}")
            return None

    def _get_txt2img(self):
        if self._txt2img_pipe is None:
            self._txt2img_pipe = self._load_diffusion(
                "stabilityai/stable-diffusion-xl-base-1.0", "txt2img"
            )
        return self._txt2img_pipe

    def _get_img2img(self):
        if self._img2img_pipe is None:
            self._img2img_pipe = self._load_diffusion(
                "stabilityai/stable-diffusion-xl-base-1.0", "img2img"
            )
        return self._img2img_pipe

    def _get_inpaint(self):
        if self._inpaint_pipe is None:
            try:
                from diffusers import StableDiffusionXLInpaintPipeline
                import torch
                self._inpaint_pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
                    "stabilityai/stable-diffusion-xl-base-1.0",
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                )
                self._inpaint_pipe = self._inpaint_pipe.to(self.device)
                if self.device == "cuda":
                    self._inpaint_pipe.enable_attention_slicing()
            except Exception as e:
                logger.error(f"Failed to load inpainting pipeline: {e}")
        return self._inpaint_pipe

    def _load_clip(self):
        if self._clip_model is None:
            try:
                from transformers import CLIPProcessor, CLIPModel
                self._clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
                self._clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
                self._clip_model.to(self.device)
            except Exception as e:
                logger.error(f"Failed to load CLIP: {e}")
        return self._clip_model, self._clip_processor

    def _load_ocr(self):
        if self._ocr_reader is None:
            try:
                import easyocr
                self._ocr_reader = easyocr.Reader(["en"], gpu=(self.device == "cuda"))
            except Exception as e:
                logger.error(f"Failed to load EasyOCR: {e}")
        return self._ocr_reader

    def _load_detr(self):
        if self._detr_model is None:
            try:
                from transformers import AutoImageProcessor, AutoModelForObjectDetection
                self._detr_processor = AutoImageProcessor.from_pretrained("facebook/detr-resnet-50")
                self._detr_model = AutoModelForObjectDetection.from_pretrained("facebook/detr-resnet-50")
                self._detr_model.to(self.device)
            except Exception as e:
                logger.error(f"Failed to load DETR: {e}")
        return self._detr_model, self._detr_processor

    def _load_segformer(self):
        if self._segformer_model is None:
            try:
                from transformers import AutoImageProcessor, AutoModelForSemanticSegmentation
                self._segformer_processor = AutoImageProcessor.from_pretrained("nvidia/segformer-b0-finetuned-ade-512-512")
                self._segformer_model = AutoModelForSemanticSegmentation.from_pretrained("nvidia/segformer-b0-finetuned-ade-512-512")
                self._segformer_model.to(self.device)
            except Exception as e:
                logger.error(f"Failed to load SegFormer: {e}")
        return self._segformer_model, self._segformer_processor

    def text_to_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
    ) -> ImageResult:
        pipe = self._get_txt2img()
        if pipe is None:
            return ImageResult(False, b"", "image/png", {}, "txt2img pipeline not loaded")
        try:
            import torch
            generator = torch.Generator(device=self.device).manual_seed(seed) if seed is not None else None
            result = pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator,
            )
            image = result.images[0]
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            return ImageResult(True, buf.getvalue(), "image/png", {"prompt": prompt, "width": width, "height": height})
        except Exception as e:
            logger.error(f"text_to_image failed: {e}")
            return ImageResult(False, b"", "image/png", {}, str(e))

    def image_to_image(
        self,
        image_bytes: bytes,
        prompt: str,
        negative_prompt: str = "",
        strength: float = 0.75,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
    ) -> ImageResult:
        pipe = self._get_img2img()
        if pipe is None:
            return ImageResult(False, b"", "image/png", {}, "img2img pipeline not loaded")
        try:
            from PIL import Image
            import torch
            init_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            init_image = init_image.resize((1024, 1024))
            generator = torch.Generator(device=self.device).manual_seed(seed) if seed is not None else None
            result = pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                image=init_image,
                strength=strength,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator,
            )
            image = result.images[0]
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            return ImageResult(True, buf.getvalue(), "image/png", {"prompt": prompt, "strength": strength})
        except Exception as e:
            logger.error(f"image_to_image failed: {e}")
            return ImageResult(False, b"", "image/png", {}, str(e))

    def inpaint(
        self,
        image_bytes: bytes,
        mask_bytes: bytes,
        prompt: str,
        negative_prompt: str = "",
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
    ) -> ImageResult:
        pipe = self._get_inpaint()
        if pipe is None:
            return ImageResult(False, b"", "image/png", {}, "inpaint pipeline not loaded")
        try:
            from PIL import Image
            import torch
            init_image = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((1024, 1024))
            mask_image = Image.open(io.BytesIO(mask_bytes)).convert("RGB").resize((1024, 1024))
            generator = torch.Generator(device=self.device).manual_seed(seed) if seed is not None else None
            result = pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                image=init_image,
                mask_image=mask_image,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator,
            )
            image = result.images[0]
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            return ImageResult(True, buf.getvalue(), "image/png", {"prompt": prompt})
        except Exception as e:
            logger.error(f"inpaint failed: {e}")
            return ImageResult(False, b"", "image/png", {}, str(e))

    def outpaint(
        self,
        image_bytes: bytes,
        expand_top: int = 0,
        expand_bottom: int = 0,
        expand_left: int = 0,
        expand_right: int = 0,
        prompt: str = "",
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
    ) -> ImageResult:
        try:
            import cv2
            import numpy as np
            from PIL import Image
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            h, w = img.shape[:2]
            new_h = h + expand_top + expand_bottom
            new_w = w + expand_left + expand_right
            canvas = np.full((new_h, new_w, 3), 0, dtype=np.uint8)
            canvas[expand_top:expand_top + h, expand_left:expand_left + w] = img
            mask = np.full((new_h, new_w), 255, dtype=np.uint8)
            mask[expand_top:expand_top + h, expand_left:expand_left + w] = 0
            mask_pil = Image.fromarray(mask)
            init_pil = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)).resize((1024, 1024))
            mask_pil = mask_pil.resize((1024, 1024))
            buf_init = io.BytesIO()
            init_pil.save(buf_init, format="PNG")
            buf_mask = io.BytesIO()
            mask_pil.save(buf_mask, format="PNG")
            return self.inpaint(
                buf_init.getvalue(),
                buf_mask.getvalue(),
                prompt or "extend the image naturally",
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
            )
        except Exception as e:
            logger.error(f"outpaint failed: {e}")
            return ImageResult(False, b"", "image/png", {}, str(e))

    def remove_background(self, image_bytes: bytes) -> ImageResult:
        try:
            from PIL import Image
            import cv2
            import numpy as np
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
            if img is None:
                return ImageResult(False, b"", "image/png", {}, "invalid image")
            if img.shape[2] == 4:
                bgra = img
            else:
                bgra = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
            gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            bgra[:, :, 3] = cv2.bitwise_and(mask, bgra[:, :, 3])
            _, encoded = cv2.imencode(".png", bgra)
            return ImageResult(True, encoded.tobytes(), "image/png", {"method": "otsu"})
        except Exception as e:
            logger.error(f"remove_background failed: {e}")
            return ImageResult(False, b"", "image/png", {}, str(e))

    def restore_face(self, image_bytes: bytes) -> ImageResult:
        try:
            import cv2
            import numpy as np
            from PIL import Image
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return ImageResult(False, b"", "image/png", {}, "invalid image")
            denoised = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            sharpened = cv2.filter2D(denoised, -1, kernel)
            lab = cv2.cvtColor(sharpened, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            lab = cv2.merge([l, a, b])
            result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            _, encoded = cv2.imencode(".png", result)
            return ImageResult(True, encoded.tobytes(), "image/png", {"method": "denoise+clahe+sharpen"})
        except Exception as e:
            logger.error(f"restore_face failed: {e}")
            return ImageResult(False, b"", "image/png", {}, str(e))

    def super_resolve(self, image_bytes: bytes, scale: int = 4) -> ImageResult:
        try:
            import cv2
            import numpy as np
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return ImageResult(False, b"", "image/png", {}, "invalid image")
            h, w = img.shape[:2]
            new_w, new_h = w * scale, h * scale
            upscaled = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            denoised = cv2.fastNlMeansDenoisingColored(upscaled, None, 5, 5, 7, 21)
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            sharpened = cv2.filter2D(denoised, -1, kernel)
            _, encoded = cv2.imencode(".png", sharpened)
            return ImageResult(True, encoded.tobytes(), "image/png", {"scale": scale, "width": new_w, "height": new_h})
        except Exception as e:
            logger.error(f"super_resolve failed: {e}")
            return ImageResult(False, b"", "image/png", {}, str(e))

    def ocr(self, image_bytes: bytes, languages: List[str] = None) -> Dict[str, Any]:
        reader = self._load_ocr()
        if reader is None:
            return {"text": "", "blocks": [], "error": "ocr engine not loaded"}
        try:
            import cv2
            import numpy as np
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return {"text": "", "blocks": [], "error": "invalid image"}
            results = reader.readtext(img, detail=1, paragraph=True)
            blocks = []
            full_text = []
            for item in results:
                if len(item) == 3:
                    bbox, text, conf = item
                else:
                    bbox, text = item
                    conf = 1.0
                blocks.append({"text": text, "confidence": float(conf), "bbox": [list(p) for p in bbox]})
                full_text.append(text)
            return {"text": "\n".join(full_text), "blocks": blocks}
        except Exception as e:
            logger.error(f"ocr failed: {e}")
            return {"text": "", "blocks": [], "error": str(e)}

    def detect_objects(self, image_bytes: bytes, threshold: float = 0.5) -> Dict[str, Any]:
        model, processor = self._load_detr()
        if model is None:
            return {"objects": [], "error": "detection model not loaded"}
        try:
            from PIL import Image
            import torch
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            inputs = processor(images=image, return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = model(**inputs)
            target_sizes = torch.tensor([image.size[::-1]], device=self.device)
            results = processor.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=threshold)
            detections = []
            for r in results:
                for score, label, box in zip(r["scores"], r["labels"], r["boxes"]):
                    detections.append({
                        "label": model.config.id2label[label.item()],
                        "score": float(score.item()),
                        "box": [float(x) for x in box.tolist()],
                    })
            return {"objects": detections}
        except Exception as e:
            logger.error(f"detect_objects failed: {e}")
            return {"objects": [], "error": str(e)}

    def segment(self, image_bytes: bytes) -> Dict[str, Any]:
        model, processor = self._load_segformer()
        if model is None:
            return {"segments": [], "error": "segmentation model not loaded"}
        try:
            from PIL import Image
            import torch
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            inputs = processor(images=image, return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = model(**inputs)
            logits = outputs.logits
            seg_map = logits.argmax(dim=1).squeeze().cpu().numpy()
            unique_labels = np.unique(seg_map)
            labels = []
            for lbl in unique_labels:
                if lbl == 0:
                    continue
                label_name = model.config.id2label.get(int(lbl), f"label_{int(lbl)}")
                labels.append({"id": int(lbl), "label": label_name})
            return {"segments": labels, "seg_map_shape": list(seg_map.shape)}
        except Exception as e:
            logger.error(f"segment failed: {e}")
            return {"segments": [], "error": str(e)}

    def caption(self, image_bytes: bytes) -> Dict[str, Any]:
        try:
            from PIL import Image
            model, processor = self._load_clip()
            if model is None:
                return {"caption": "", "error": "clip not loaded"}
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            inputs = processor(images=image, return_tensors="pt").to(self.device)
            with torch.no_grad():
                image_features = model.get_image_features(**inputs)
            text_candidates = [
                "a photo of a person",
                "a photo of an animal",
                "a photo of a landscape",
                "a photo of a building",
                "a photo of a vehicle",
                "a photo of food",
                "a photo of a document",
                "a photo of a screen",
                "a photo of nature",
                "a photo of art",
            ]
            text_inputs = processor(text=text_candidates, return_tensors="pt", padding=True).to(self.device)
            with torch.no_grad():
                text_features = model.get_text_features(**text_inputs)
            scores = (image_features @ text_features.T).softmax(dim=-1).squeeze(0)
            best_idx = int(scores.argmax().item())
            return {"caption": text_candidates[best_idx], "scores": {text_candidates[i]: float(scores[i].item()) for i in range(len(text_candidates))}}
        except Exception as e:
            logger.error(f"caption failed: {e}")
            return {"caption": "", "error": str(e)}
