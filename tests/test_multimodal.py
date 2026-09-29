from __future__ import annotations

import pytest
import torch

ROOT = __import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
if ROOT not in __import__("sys").path:
    __import__("sys").path.insert(0, ROOT)

from models.llm.multimodal.vision import VisionEncoder, preprocess_image, resize_image
from models.llm.multimodal.ocr import OCRTool
from models.llm.multimodal.speech import SpeechEncoder, WhisperStyleSTT, AudioPreprocessor
from models.llm.multimodal.tts import SpeechSynthesizer
from models.llm.multimodal.image_understanding import (
    ImageCaptioner,
    VisualQuestionAnswerer,
    ObjectDetector,
)
from models.llm.multimodal.document import DocumentParser, LayoutAnalyzer, TableExtractor
from models.llm.multimodal.video import VideoEncoder, sample_frames_uniform, sample_frames_adaptive
from models.llm.multimodal.cross_modal import MultiModalEmbedder, SimilaritySearch, RetrievalAugmentedGenerator


@pytest.fixture
def tiny_vision_config():
    return {
        "image_size": 32,
        "patch_size": 8,
        "num_channels": 3,
        "hidden_size": 64,
        "num_layers": 2,
        "num_attention_heads": 4,
        "mlp_ratio": 2.0,
        "dropout": 0.0,
    }


@pytest.fixture
def tiny_speech_config():
    return {
        "num_mel_bins": 16,
        "hidden_size": 64,
        "num_layers": 2,
        "num_attention_heads": 4,
        "dropout": 0.0,
    }


class TestVisionEncoder:
    def test_initializes(self, tiny_vision_config):
        model = VisionEncoder(**tiny_vision_config)
        assert model is not None

    def test_forward_shape(self, tiny_vision_config):
        model = VisionEncoder(**tiny_vision_config)
        model.eval()
        x = torch.randn(2, 3, 32, 32)
        with torch.no_grad():
            out = model(x)
        assert out.shape == (2, (32 // 8) ** 2 + 1, 64)

    def test_get_image_embedding(self, tiny_vision_config):
        model = VisionEncoder(**tiny_vision_config)
        model.eval()
        x = torch.randn(2, 3, 32, 32)
        with torch.no_grad():
            emb = model.get_image_embedding(x)
        assert emb.shape == (2, 64)

    def test_get_patch_embeddings(self, tiny_vision_config):
        model = VisionEncoder(**tiny_vision_config)
        model.eval()
        x = torch.randn(2, 3, 32, 32)
        with torch.no_grad():
            patches = model.get_patch_embeddings(x)
        assert patches.shape == (2, (32 // 8) ** 2, 64)

    def test_preprocess_image(self):
        x = torch.randint(0, 256, (2, 3, 32, 32), dtype=torch.uint8)
        out = preprocess_image(x)
        assert out.dtype == torch.float32
        assert out.shape == (2, 3, 32, 32)

    def test_resize_image(self):
        x = torch.randn(2, 3, 64, 64)
        out = resize_image(x, 32)
        assert out.shape == (2, 3, 32, 32)


class TestOCRTool:
    def test_initializes(self):
        tool = OCRTool(engine="easyocr")
        assert tool.engine == "easyocr"

    def test_clean_text(self):
        text = "Hello   world\n\n\n\nFoo bar"
        cleaned = OCRTool.clean_text(text)
        assert cleaned == "Hello world\n\nFoo bar"

    def test_extract_structured_no_reader(self):
        tool = OCRTool(engine="easyocr")
        result = tool.extract_structured(None)
        assert "text" in result
        assert "lines" in result
        assert "num_lines" in result


class TestSpeechEncoder:
    def test_initializes(self, tiny_speech_config):
        model = SpeechEncoder(**tiny_speech_config)
        assert model is not None

    def test_forward_shape(self, tiny_speech_config):
        model = SpeechEncoder(**tiny_speech_config)
        model.eval()
        mel = torch.randn(2, 16, 128)
        with torch.no_grad():
            out = model(mel)
        assert out.ndim == 3
        assert out.size(0) == 2

    def test_whisper_stt(self):
        model = WhisperStyleSTT(
            vocab_size=100,
            num_mel_bins=16,
            hidden_size=64,
            encoder_num_layers=2,
            decoder_num_layers=2,
            num_attention_heads=4,
        )
        model.eval()
        mel = torch.randn(1, 16, 128)
        input_ids = torch.tensor([[0]])
        with torch.no_grad():
            out = model(mel, input_ids)
        assert out.ndim == 3

    def test_audio_preprocessor_normalize(self):
        audio = torch.tensor([1.0, -2.0, 3.0])
        norm = AudioPreprocessor.normalize(audio)
        assert float(norm.abs().max()) == pytest.approx(1.0, abs=1e-5)

    def test_audio_preprocessor_pad(self):
        audio = torch.zeros(1, 10)
        padded = AudioPreprocessor.pad_or_trim(audio, 20)
        assert padded.shape[-1] == 20


class TestSpeechSynthesizer:
    def test_initializes(self):
        model = SpeechSynthesizer(vocab_size=100, hidden_size=32)
        assert model is not None

    def test_forward(self):
        model = SpeechSynthesizer(vocab_size=100, hidden_size=32)
        model.eval()
        input_ids = torch.randint(0, 100, (2, 16))
        with torch.no_grad():
            wav, mu, logvar = model(input_ids)
        assert wav.ndim == 2
        assert wav.size(0) == 2

    def test_synthesize(self):
        model = SpeechSynthesizer(vocab_size=100, hidden_size=32)
        model.eval()
        input_ids = torch.randint(0, 100, (2, 16))
        with torch.no_grad():
            wav = model.synthesize(input_ids)
        assert wav.ndim == 2
        assert wav.size(0) == 2


class TestImageUnderstanding:
    def test_image_captioner(self):
        model = ImageCaptioner(vocab_size=100, hidden_size=64, num_attention_heads=4)
        model.eval()
        vision_embeds = torch.randn(2, 10, 64)
        with torch.no_grad():
            logits = model(vision_embeds, torch.tensor([[1], [1]]))
        assert logits.shape[-1] == 100

    def test_visual_question_answerer(self):
        model = VisualQuestionAnswerer(vocab_size=100, hidden_size=64, num_attention_heads=4)
        model.eval()
        vision_embeds = torch.randn(2, 10, 64)
        with torch.no_grad():
            logits = model(vision_embeds, torch.tensor([[1, 2], [1, 2]]))
        assert logits.shape[-1] == 100

    def test_object_detector(self):
        model = ObjectDetector(hidden_size=64, num_queries=10, num_classes=5)
        model.eval()
        vision_embeds = torch.randn(2, 10, 64)
        with torch.no_grad():
            logits, boxes = model(vision_embeds)
        assert logits.shape == (2, 10, 6)
        assert boxes.shape == (2, 10, 4)
        assert torch.all((boxes >= 0) & (boxes <= 1))


class TestDocumentModules:
    def test_document_parser(self):
        model = DocumentParser(hidden_size=64, vocab_size=100, num_attention_heads=4)
        model.eval()
        x = torch.randn(2, 16, 64)
        with torch.no_grad():
            logits = model(x)
        assert logits.shape[-1] == 100

    def test_layout_analyzer(self):
        model = LayoutAnalyzer(hidden_size=64, num_classes=5)
        model.eval()
        x = torch.randn(2, 16, 64)
        with torch.no_grad():
            result = model.predict_layout(x)
        assert "layout_classes" in result
        assert "bounding_boxes" in result

    def test_table_extractor(self):
        model = TableExtractor(hidden_size=64, max_cells=20)
        model.eval()
        x = torch.randn(2, 16, 64)
        with torch.no_grad():
            result = model.extract_table(x)
        assert "cell_logits" in result
        assert "cell_boxes" in result


class TestVideoEncoder:
    def test_initializes(self):
        model = VideoEncoder(num_frames=4, hidden_size=64)
        assert model is not None

    def test_forward(self):
        model = VideoEncoder(num_frames=4, hidden_size=64)
        model.eval()
        frame_embeds = torch.randn(2, 8, 64)
        with torch.no_grad():
            out = model(frame_embeds)
        assert out.shape == (2, 4, 64)

    def test_get_video_embedding(self):
        model = VideoEncoder(num_frames=4, hidden_size=64)
        model.eval()
        frame_embeds = torch.randn(2, 8, 64)
        with torch.no_grad():
            emb = model.get_video_embedding(frame_embeds)
        assert emb.shape == (2, 64)

    def test_sample_frames_uniform(self):
        indices = sample_frames_uniform(total_frames=20, num_samples=5)
        assert len(indices) == 5
        assert indices == sorted(indices)

    def test_sample_frames_adaptive(self):
        scores = torch.randn(10)
        indices = sample_frames_adaptive(scores, num_samples=5)
        assert len(indices) == 5
        assert indices == sorted(indices)


class TestCrossModal:
    def test_multimodal_embedder(self):
        embedder = MultiModalEmbedder(vision_hidden_size=64, text_hidden_size=64, projection_dim=32)
        vision = torch.randn(2, 10, 64)
        text = torch.randn(2, 10, 64)
        v, t = embedder(vision, text)
        assert v.shape == (2, 32)
        assert t.shape == (2, 32)

    def test_compute_similarity(self):
        embedder = MultiModalEmbedder(vision_hidden_size=64, text_hidden_size=64, projection_dim=32)
        vision = torch.randn(2, 10, 64)
        text = torch.randn(2, 10, 64)
        sim = embedder.compute_similarity(vision, text)
        assert sim.shape == (2, 2)

    def test_similarity_search(self):
        embedder = MultiModalEmbedder(vision_hidden_size=64, text_hidden_size=64, projection_dim=32)
        search = SimilaritySearch(embedder)
        vision_list = [torch.randn(1, 10, 64) for _ in range(3)]
        search.build_index(vision_list, [{"id": i} for i in range(3)])
        query = torch.randn(1, 10, 64)
        results = search.search(query, top_k=2)
        assert len(results) == 2
        assert "score" in results[0]

    def test_retrieval_augmented_generator(self):
        model = RetrievalAugmentedGenerator(hidden_size=64, num_attention_heads=4)
        model.eval()
        query = torch.randn(1, 10, 64)
        context = torch.randn(1, 10, 64)
        input_ids = torch.tensor([[1, 2, 3]])
        with torch.no_grad():
            logits = model(query, context, input_ids)
        assert logits.shape[-1] == 32000
