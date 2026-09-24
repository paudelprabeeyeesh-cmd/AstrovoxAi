import numpy as np
import pytest
from emergent_abilities.in_context_learning import InContextLearningModel, TaskIdentifier, ICLDynamicsAnalyzer


class TestInContextLearningModel:
    def test_forward_output_shape(self):
        model = InContextLearningModel(vocab_size=100, embedding_dim=32, num_heads=4)
        ctx = np.random.randn(5, 32)
        query = np.random.randn(32)
        logits = model.forward(ctx, query)
        assert logits.shape == (100,)

    def test_predict_with_no_context(self):
        model = InContextLearningModel(vocab_size=50, embedding_dim=16, num_heads=2)
        result = model.predict([], np.random.randn(16))
        assert result.in_context_benefit == 0.0
        assert 0 <= result.predicted_token < 50

    def test_predict_with_context(self):
        model = InContextLearningModel(vocab_size=100, embedding_dim=32, num_heads=4)
        ctx = [(np.random.randn(32), i % 3) for i in range(5)]
        query = np.random.randn(32)
        result = model.predict(ctx, query)
        assert 0 <= result.predicted_token < 100
        assert 0.0 <= result.confidence <= 1.0
        assert result.in_context_benefit > 0.0

    def test_attention_output_shape(self):
        model = InContextLearningModel(vocab_size=100, embedding_dim=32, num_heads=4)
        q = np.random.randn(32)
        k = np.random.randn(5, 32)
        v = np.random.randn(5, 100)
        out = model.attention(q, k, v)
        assert out.shape == (100,)


class TestTaskIdentifier:
    def test_identify_task_without_prototypes(self):
        identifier = TaskIdentifier(num_tasks=3)
        result = identifier.identify_task([], np.random.randn(16))
        assert result == 0

    def test_identify_task_with_prototypes(self):
        identifier = TaskIdentifier(num_tasks=3)
        identifier.task_prototypes = {0: np.random.randn(16), 1: np.random.randn(16)}
        query = identifier.task_prototypes[1]
        result = identifier.identify_task([], query)
        assert result == 1

    def test_update_task_prototype(self):
        identifier = TaskIdentifier(num_tasks=3)
        emb = np.random.randn(16)
        identifier.update_task_prototype(0, emb)
        assert 0 in identifier.task_prototypes
        identifier.update_task_prototype(0, emb)
        assert np.allclose(identifier.task_prototypes[0], 0.9 * emb + 0.1 * emb)


class TestICLDynamicsAnalyzer:
    def test_record_performance(self):
        analyzer = ICLDynamicsAnalyzer()
        analyzer.record_performance(num_shots=5, performance=0.8)
        assert len(analyzer.shot_performance[5]) == 1

    def test_learning_curve(self):
        analyzer = ICLDynamicsAnalyzer()
        analyzer.record_performance(1, 0.3)
        analyzer.record_performance(5, 0.6)
        curve = analyzer.learning_curve()
        assert len(curve) == 11

    def test_sensitivity_to_context(self):
        analyzer = ICLDynamicsAnalyzer()
        for i in range(11):
            analyzer.record_performance(i, float(i) / 10.0)
        sensitivity = analyzer.sensitivity_to_context()
        assert sensitivity > 0.0
