import numpy as np
from advanced_learning.zero_shot_learning import ZeroShotLearner, CLIPConfig


class TestZeroShotLearner:
    def test_initialization(self):
        config = CLIPConfig(visual_input_dim=32, text_input_dim=16)
        zsl = ZeroShotLearner(config)
        assert zsl.config.visual_input_dim == 32
        assert zsl.config.text_input_dim == 16
        assert zsl.config.embedding_dim == 256
        assert len(zsl.loss_history) == 0

    def test_encode_visual(self):
        config = CLIPConfig(visual_input_dim=32, text_input_dim=16, embedding_dim=64)
        zsl = ZeroShotLearner(config)
        x = np.random.randn(8, 32).astype(np.float64)
        z = zsl._encode_visual(x)
        assert z.shape == (8, 64)

    def test_encode_text(self):
        config = CLIPConfig(visual_input_dim=32, text_input_dim=16, embedding_dim=64)
        zsl = ZeroShotLearner(config)
        x = np.random.randn(8, 16).astype(np.float64)
        z = zsl._encode_text(x)
        assert z.shape == (8, 64)

    def test_train_step(self):
        config = CLIPConfig(visual_input_dim=32, text_input_dim=16)
        zsl = ZeroShotLearner(config)
        images = np.random.randn(8, 32).astype(np.float64)
        texts = np.random.randn(8, 16).astype(np.float64)
        result = zsl.train_step(images, texts)
        assert "loss" in result
        assert "temperature" in result
        assert len(zsl.loss_history) == 1

    def test_zero_shot_classify(self):
        config = CLIPConfig(visual_input_dim=32, text_input_dim=16, embedding_dim=64)
        zsl = ZeroShotLearner(config)
        image = np.random.randn(1, 32).astype(np.float64)
        class_texts = [np.random.randn(16).astype(np.float64) for _ in range(5)]
        label = zsl.zero_shot_classify(image, class_texts)
        assert 0 <= label < 5

    def test_get_report(self):
        config = CLIPConfig(visual_input_dim=32, text_input_dim=16)
        zsl = ZeroShotLearner(config)
        images = np.random.randn(8, 32).astype(np.float64)
        texts = np.random.randn(8, 16).astype(np.float64)
        zsl.train_step(images, texts)
        report = zsl.get_report()
        assert "num_steps" in report
        assert "temperature" in report
