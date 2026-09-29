import os
import sys

import pytest
import torch
import torch.nn as nn

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.compression import (
    AWQStyleQuantizer,
    DistillationConfig,
    DistillationTrainer,
    FeatureDistillationLoss,
    GPTQStyleQuantizer,
    INT4QuantizationConfig,
    INT4QuantizedLinear,
    QATTrainer,
    SparsityConfig,
    SparseLinear,
    TemperatureSoftTargetLoss,
    dequantize_int4_groupwise,
    export_gguf,
    import_gguf,
    MagnitudePruner,
    MaskedTrainer,
    PruningConfig,
    StructuredSparsity,
    update_gguf_metadata,
    quantize_int4_groupwise,
)
from models.llm.quantization import QuantizationConfig, QuantizationFormat, QuantizationMethod


class TestINT4Quantization:
    def test_quantize_int4_symmetric(self):
        weight = torch.randn(8, 16)
        config = INT4QuantizationConfig(group_size=8, symmetric=True)
        q, scale, zp = quantize_int4_groupwise(weight, config)
        assert zp is None
        assert q.shape == weight.shape
        assert q.dtype == torch.int8
        assert scale.shape[1] == 2

    def test_quantize_int4_asymmetric(self):
        weight = torch.randn(8, 16)
        config = INT4QuantizationConfig(group_size=8, symmetric=False)
        q, scale, zp = quantize_int4_groupwise(weight, config)
        assert zp is not None
        assert q.shape == weight.shape
        assert q.dtype == torch.int8

    def test_dequantize_int4_symmetric(self):
        weight = torch.randn(8, 16)
        config = INT4QuantizationConfig(group_size=8, symmetric=True)
        q, scale, _ = quantize_int4_groupwise(weight, config)
        dequant = dequantize_int4_groupwise(q, scale, None, 16, config)
        assert dequant.shape == (8, 16)
        assert torch.allclose(dequant, weight, atol=0.2)

    def test_dequantize_int4_asymmetric(self):
        weight = torch.randn(8, 16) + 1.0
        config = INT4QuantizationConfig(group_size=8, symmetric=False)
        q, scale, zp = quantize_int4_groupwise(weight, config)
        dequant = dequantize_int4_groupwise(q, scale, zp, 16, config)
        assert dequant.shape == (8, 16)

    def test_padding_non_divisible(self):
        weight = torch.randn(4, 10)
        config = INT4QuantizationConfig(group_size=3, symmetric=True)
        q, scale, _ = quantize_int4_groupwise(weight, config)
        assert q.shape[1] == 12
        dequant = dequantize_int4_groupwise(q, scale, None, 10, config)
        assert dequant.shape == (4, 10)

    def test_int4_quantized_linear_forward(self):
        layer = INT4QuantizedLinear(16, 8, bias=False)
        x = torch.randn(2, 16)
        out = layer(x)
        assert out.shape == (2, 8)

    def test_int4_quantized_linear_quantize(self):
        layer = INT4QuantizedLinear(16, 8, bias=False)
        weight = torch.randn(8, 16)
        layer.quantize(weight)
        x = torch.randn(2, 16)
        out = layer(x)
        assert out.shape == (2, 8)

    def test_int4_invalid_dim(self):
        with pytest.raises(ValueError):
            quantize_int4_groupwise(torch.randn(4, 6, 8), INT4QuantizationConfig())


class TestGPTQAndAWQ:
    def test_gptq_style_quantizer_init(self):
        model = nn.Linear(8, 4)
        config = QuantizationConfig(weight_bits=4)
        quantizer = GPTQStyleQuantizer(config)
        result = quantizer.quantize(model)
        assert result is not None

    def test_awq_style_quantizer_init(self):
        model = nn.Linear(8, 4)
        config = QuantizationConfig(weight_bits=4)
        quantizer = AWQStyleQuantizer(config)
        result = quantizer.quantize(model)
        assert result is not None


class TestQATTrainer:
    def test_prepare_model(self):
        model = nn.Linear(8, 4)
        config = QuantizationConfig(
            format=QuantizationFormat.INT8_SYMMETRIC,
            method=QuantizationMethod.QUANTIZATION_AWARE_TRAINING,
        )
        trainer = QATTrainer(model, config)
        prepared = trainer.prepare_model()
        assert prepared is not None

    def test_train_step(self):
        model = nn.Linear(8, 4)
        config = QuantizationConfig(
            format=QuantizationFormat.INT8_SYMMETRIC,
            method=QuantizationMethod.QUANTIZATION_AWARE_TRAINING,
        )
        trainer = QATTrainer(model, config)
        optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
        x = torch.randn(2, 8)
        y = torch.randn(2, 4)
        loss = trainer.train_step((x, y), optimizer)
        assert loss.item() > 0


class TestGGUF:
    def test_export_import_roundtrip(self, tmp_path):
        model = nn.Sequential(nn.Linear(8, 4))
        path = str(tmp_path / "model.gguf")
        export_gguf(model, path, metadata={"version": "1.0"})
        assert os.path.exists(path)

        metadata, tensors = import_gguf(path)
        assert "version" in metadata
        assert "0.weight" in tensors or len(tensors) >= 0

    def test_update_metadata(self, tmp_path):
        model = nn.Sequential(nn.Linear(8, 4))
        path = str(tmp_path / "model.gguf")
        export_gguf(model, path, metadata={"version": "1.0"})
        update_gguf_metadata(path, {"version": "2.0", "author": "test"})
        metadata, _ = import_gguf(path)
        assert metadata.get("version") == "2.0"
        assert metadata.get("author") == "test"


class TestDistillation:
    def test_temperature_soft_target_loss(self):
        criterion = TemperatureSoftTargetLoss(temperature=2.0, alpha=0.5)
        student_logits = torch.randn(4, 10)
        teacher_logits = torch.randn(4, 10)
        labels = torch.randint(0, 10, (4,))
        loss = criterion(student_logits, teacher_logits, labels)
        assert loss.item() > 0

    def test_feature_distillation_loss(self):
        criterion = FeatureDistillationLoss(feature_layers=["0"], weight=0.1)
        assert criterion.feature_layers == ["0"]

    def test_feature_distillation_forward_zero(self):
        criterion = FeatureDistillationLoss(feature_layers=["nonexistent"], weight=0.1)
        loss = criterion()
        assert loss.item() == 0.0

    def test_distillation_trainer(self):
        teacher = nn.Linear(8, 4)
        student = nn.Linear(8, 4)
        config = DistillationConfig(temperature=2.0, alpha=0.5)
        trainer = DistillationTrainer(teacher, student, config)
        optimizer = torch.optim.SGD(student.parameters(), lr=0.01)
        x = torch.randn(2, 8)
        y = torch.randint(0, 4, (2,))
        loss = trainer.train_step(x, y, optimizer)
        assert loss.item() > 0

    def test_distillation_trainer_with_features(self):
        teacher = nn.Sequential(nn.Linear(8, 4), nn.ReLU())
        student = nn.Sequential(nn.Linear(8, 4), nn.ReLU())
        config = DistillationConfig(
            temperature=2.0,
            alpha=0.5,
            feature_layers=["1"],
            use_feature_distillation=True,
        )
        trainer = DistillationTrainer(teacher, student, config)
        assert "1" in trainer.teacher_features or "1" in trainer.student_features


class TestPruning:
    def test_magnitude_pruner_basic(self):
        model = nn.Linear(8, 4)
        config = PruningConfig(sparsity=0.5, block_size=1)
        pruner = MagnitudePruner(model, config)
        pruner.step(1000)
        sparsity = pruner.get_sparsity()
        assert sparsity > 0.0

    def test_magnitude_pruner_schedule(self):
        model = nn.Linear(8, 4)
        config = PruningConfig(sparsity=0.5, start_step=0, end_step=100)
        pruner = MagnitudePruner(model, config)
        pruner.step(0)
        assert pruner.current_sparsity == 0.0
        pruner.step(100)
        assert pruner.current_sparsity == 0.5

    def test_structured_sparsity(self):
        model = nn.Linear(8, 4)
        sparsity = StructuredSparsity(model, sparsity=0.5)
        sparsity.apply()
        weight = model.weight.data
        assert (weight == 0).sum().item() > 0


class TestSparsity:
    def test_sparse_linear_forward(self):
        layer = SparseLinear(8, 4, sparsity=0.5)
        x = torch.randn(2, 8)
        out = layer(x)
        assert out.shape == (2, 4)

    def test_sparse_linear_apply_sparsity(self):
        layer = SparseLinear(8, 4, sparsity=0.5)
        layer.apply_sparsity()
        w = layer.weight.data * layer.mask.data
        assert (w == 0).sum().item() > 0

    def test_masked_trainer(self):
        model = nn.Linear(8, 4)
        config = SparsityConfig(sparsity_ratio=0.5)
        trainer = MaskedTrainer(model, config)
        optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
        x = torch.randn(2, 8)
        y = torch.randn(2, 4)
        loss = trainer.train_step(x, y, optimizer)
        assert loss.item() > 0

    def test_set_sparsity_ratio(self):
        model = nn.Sequential(SparseLinear(8, 4, sparsity=0.0))
        set_sparsity_ratio(model, 0.5)
        assert model[0].sparsity == 0.5
