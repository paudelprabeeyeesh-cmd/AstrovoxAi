import numpy as np
import pytest
from emergent_abilities.instruction_following import InstructionFollowingModel, InstructionTuningAnalyzer, GeneralizationGapAnalyzer


class TestInstructionFollowingModel:
    def test_follow_instruction_output_shape(self):
        model = InstructionFollowingModel(vocab_size=100, instruction_dim=16, hidden_dim=32)
        instruction_vec = np.random.randn(16)
        tokens, confidence = model.follow_instruction(instruction_vec)
        assert isinstance(tokens, np.ndarray)
        assert 0.0 <= confidence <= 1.0

    def test_follow_instruction_top_k(self):
        model = InstructionFollowingModel(vocab_size=100, instruction_dim=16, hidden_dim=32)
        instruction_vec = np.random.randn(16)
        tokens, confidence = model.follow_instruction(instruction_vec, top_k=3)
        assert len(tokens) == 3

    def test_encode_instruction_shape(self):
        model = InstructionFollowingModel(vocab_size=100, instruction_dim=16, hidden_dim=32)
        vec = np.random.randn(16)
        encoding = model.encode_instruction(vec)
        assert encoding.shape == (32,)

    def test_instruction_consistency(self):
        model = InstructionFollowingModel(vocab_size=100, instruction_dim=16, hidden_dim=32)
        vec = np.random.randn(16)
        consistency = model.instruction_consistency(vec, num_samples=10)
        assert 0.0 <= consistency <= 1.0


class TestInstructionTuningAnalyzer:
    def test_record_performance(self):
        analyzer = InstructionTuningAnalyzer()
        analyzer.record_pre_tuning_loss(loss=2.5, instruction_type="summarization")
        assert len(analyzer.loss_before_tuning) == 1

    def test_record_post_tuning_loss(self):
        analyzer = InstructionTuningAnalyzer()
        analyzer.record_pre_tuning_loss(loss=2.5, instruction_type="qa")
        analyzer.record_post_tuning_loss(loss=1.2)
        assert len(analyzer.loss_after_tuning) == 1

    def test_improvement_by_type(self):
        analyzer = InstructionTuningAnalyzer()
        analyzer.record_pre_tuning_loss(loss=2.0, instruction_type="qa")
        analyzer.record_post_tuning_loss(loss=1.0)
        improvements = analyzer.improvement_by_type()
        assert "qa" in improvements
        assert pytest.approx(improvements["qa"], rel=1e-5) == 1.0

    def test_overall_improvement(self):
        analyzer = InstructionTuningAnalyzer()
        analyzer.record_pre_tuning_loss(loss=2.0, instruction_type="qa")
        analyzer.record_post_tuning_loss(loss=1.0)
        improvement = analyzer.overall_improvement()
        assert pytest.approx(improvement, rel=1e-5) == 1.0


class TestGeneralizationGapAnalyzer:
    def test_compute_gap(self):
        analyzer = GeneralizationGapAnalyzer()
        analyzer.record(train_perf=0.95, test_perf=0.80)
        analyzer.record(train_perf=0.93, test_perf=0.78)
        gap = analyzer.compute_gap()
        assert pytest.approx(gap, rel=1e-5) == 0.15

    def test_empty_records(self):
        analyzer = GeneralizationGapAnalyzer()
        gap = analyzer.compute_gap()
        assert gap == 0.0
