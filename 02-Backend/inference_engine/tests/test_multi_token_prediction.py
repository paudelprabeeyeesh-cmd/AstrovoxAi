
import numpy as np

from inference_engine.multi_token_prediction import (
    MultiTokenPredictor, MTPConfig, MTPModule
)


def test_mtp_predict():
    predictor = MultiTokenPredictor(MTPConfig(num_predictions=3, hidden_size=64, vocab_size=100))
    tokens = predictor.predict([1, 2, 3], num_steps=3)
    assert len(tokens) == 3
    for t in tokens:
        assert 0 <= t < 100


def test_mtp_training_step():
    predictor = MultiTokenPredictor(MTPConfig(num_predictions=3, hidden_size=64, vocab_size=100))
    input_ids = np.array([[1, 2, 3]], dtype=np.int64)
    target_ids = np.array([10, 20, 30])
    result = predictor.training_step(input_ids, target_ids, learning_rate=0.001)
    assert "loss" in result
    assert "accuracy" in result
    assert result["num_predictions"] == 3


def test_mtp_training_stats():
    predictor = MultiTokenPredictor(MTPConfig(num_predictions=3, hidden_size=64, vocab_size=100))
    stats = predictor.get_training_stats()
    assert stats["num_steps"] == 0
    assert stats["avg_accuracy"] == 0.0
    input_ids = np.array([[1, 2, 3]], dtype=np.int64)
    target_ids = np.array([10, 20, 30])
    predictor.training_step(input_ids, target_ids)
    stats = predictor.get_training_stats()
    assert stats["num_steps"] == 1
    assert 0.0 <= stats["last_accuracy"] <= 1.0


def test_mtp_config_defaults():
    config = MTPConfig()
    assert config.num_predictions == 3
    assert config.hidden_size == 128
    assert config.vocab_size == 1000


def test_mtp_module_forward():
    module = MTPModule(MTPConfig(num_predictions=4, hidden_size=64, vocab_size=100))
    input_ids = np.array([[1, 2, 3]], dtype=np.int64)
    result = module.forward(input_ids)
    assert "hidden" in result
    assert "predictions" in result
    assert len(result["predictions"]) == 4
    for p in result["predictions"]:
        assert p.shape[-1] == 100
