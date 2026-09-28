import importlib.util
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

_model_scaling_spec = importlib.util.spec_from_file_location(
    "model.model_scaling", os.path.join(ROOT, "model", "model_scaling.py")
)
_model_scaling_mod = importlib.util.module_from_spec(_model_scaling_spec)
_model_scaling_spec.loader.exec_module(_model_scaling_mod)
count_parameters = _model_scaling_mod.count_parameters
memory_estimation = _model_scaling_mod.memory_estimation
chinchilla_optimal_tokens = _model_scaling_mod.chinchilla_optimal_tokens
estimate_training_time = _model_scaling_mod.estimate_training_time
load_config = _model_scaling_mod.load_config
estimate_config = _model_scaling_mod.estimate_config
hardware_requirements = _model_scaling_mod.hardware_requirements
training_recipe = _model_scaling_mod.training_recipe
compare_configs = _model_scaling_mod.compare_configs

CONFIG_100M = os.path.join(ROOT, "models", "llm", "configs", "config_100m.yaml")


class TestModelScaling:
    def test_count_parameters_matches_config(self):
        if not os.path.exists(CONFIG_100M):
            pytest.skip("config_100m.yaml not found")
        config = load_config(CONFIG_100M)
        params = count_parameters(
            vocab_size=int(config["vocab_size"]),
            hidden_size=int(config["hidden_size"]),
            num_hidden_layers=int(config["num_hidden_layers"]),
            num_attention_heads=int(config["num_attention_heads"]),
            intermediate_size=int(config["intermediate_size"]),
            max_position_embeddings=int(config.get("max_position_embeddings", 2048)),
            attention_bias=bool(config.get("attention_bias", False)),
            mlp_bias=bool(config.get("mlp_bias", False)),
            tie_weights=bool(config.get("tie_weights", True)),
            activation=str(config.get("activation", "swiglu")),
        )
        assert params > 0
        assert params < 1_000_000_000

    def test_memory_estimation(self):
        mem = memory_estimation(
            num_params=10_000_000, dtype_bytes=2, training=True, context_length=1024, batch_size=1
        )
        assert mem["weights_gb"] > 0
        assert mem["total_base_gb"] > mem["weights_gb"]

    def test_memory_no_training(self):
        mem = memory_estimation(num_params=10_000_000, training=False)
        assert mem["gradients_gb"] == 0
        assert mem["optimizer_gb"] == 0

    def test_chinchilla_optimal_tokens(self):
        tokens = chinchilla_optimal_tokens(num_params=1_000_000)
        assert tokens == 20_000_000

    def test_estimate_training_time(self):
        result = estimate_training_time(
            num_params=100_000_000, tokens_per_second=1000, context_length=1024
        )
        assert "steps" in result
        assert "days" in result
        assert result["steps"] > 0

    def test_estimate_config(self):
        if not os.path.exists(CONFIG_100M):
            pytest.skip("config_100m.yaml not found")
        report = estimate_config(CONFIG_100M)
        assert "num_params" in report
        assert "memory" in report
        assert report["num_params"] > 0

    def test_hardware_requirements_small(self):
        if not os.path.exists(CONFIG_100M):
            pytest.skip("config_100m.yaml not found")
        hw = hardware_requirements(CONFIG_100M)
        assert "model_size" in hw
        assert "runnable_locally" in hw

    def test_training_recipe_small(self):
        if not os.path.exists(CONFIG_100M):
            pytest.skip("config_100m.yaml not found")
        recipe = training_recipe(CONFIG_100M)
        assert "optimizer" in recipe
        assert "lr" in recipe

    def test_compare_configs(self):
        base_dir = os.path.join(ROOT, "models", "llm", "configs")
        if not os.path.exists(base_dir):
            pytest.skip("configs dir not found")
        result = compare_configs(base_dir=base_dir)
        assert isinstance(result, str)
        assert len(result) > 0
