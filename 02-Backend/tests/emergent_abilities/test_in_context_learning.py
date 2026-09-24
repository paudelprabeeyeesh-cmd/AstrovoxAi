import random
import pytest
from emergent_abilities.in_context_learning import (
    ICLDynamicsAnalyzer,
    ICLResult,
    InContextLearningModel,
    TaskIdentifier,
    _attention,
    _dot,
    _matmul_vec,
    _normalize,
    _softmax,
    _transpose,
)


class TestHelpers:
    def test_dot_product(self):
        assert _dot([1.0, 2.0, 3.0], [4.0, 5.0, 6.0]) == pytest.approx(32.0)

    def test_dot_zero(self):
        assert _dot([0.0, 0.0], [1.0, 2.0]) == 0.0

    def test_norm_nonzero(self):
        assert _normalize([3.0, 4.0]) == pytest.approx([0.6, 0.8])

    def test_norm_zero(self):
        result = _normalize([0.0, 0.0])
        assert result == [0.0, 0.0]

    def test_softmax(self):
        result = _softmax([0.0, 1.0, 2.0])
        total = sum(result)
        assert abs(total - 1.0) < 1e-6
        assert result.index(max(result)) == 2

    def test_softmax_sum_one(self):
        result = _softmax([1.0, 1.0, 1.0])
        assert abs(sum(result) - 1.0) < 1e-6

    def test_matmul_vec(self):
        matrix = [[1.0, 2.0], [3.0, 4.0]]
        vec = [1.0, 1.0]
        result = _matmul_vec(matrix, vec)
        assert result == pytest.approx([3.0, 7.0])

    def test_transpose(self):
        m = [[1.0, 2.0], [3.0, 4.0]]
        result = _transpose(m)
        assert result == [[1.0, 3.0], [2.0, 4.0]]

    def test_transpose_empty(self):
        assert _transpose([]) == []

    def test_attention(self):
        query = [1.0, 0.0]
        keys = [[1.0, 0.0], [0.0, 1.0]]
        values = [[1.0, 0.0], [0.0, 1.0]]
        result = _attention(query, keys, values)
        assert len(result) == 2
        assert abs(sum(result) - 1.0) < 1e-6


class TestICLResult:
    def test_default_values(self):
        r = ICLResult(predicted_token=3, confidence=0.9, task_confidence=0.8, in_context_benefit=0.5)
        assert r.predicted_token == 3
        assert r.confidence == 0.9
        assert r.task_confidence == 0.8
        assert r.in_context_benefit == 0.5


class TestInContextLearningModel:
    def test_initialization(self):
        model = InContextLearningModel(vocab_size=100, embedding_dim=16, num_heads=4)
        assert model.vocab_size == 100
        assert model.embedding_dim == 16
        assert model.num_heads == 4

    def test_predict_no_context(self):
        model = InContextLearningModel(vocab_size=50, embedding_dim=8, num_heads=2)
        result = model.predict([], [random.gauss(0, 1) for _ in range(8)])
        assert isinstance(result, ICLResult)
        assert result.confidence == 0.0
        assert result.in_context_benefit == 0.0

    def test_predict_with_context(self):
        random.seed(42)
        model = InContextLearningModel(vocab_size=50, embedding_dim=8, num_heads=2)
        ctx = [([random.gauss(0, 1) for _ in range(8)], i % 2) for i in range(5)]
        query = [random.gauss(0, 1) for _ in range(8)]
        result = model.predict(ctx, query)
        assert 0 <= result.predicted_token < 50
        assert 0.0 <= result.confidence <= 1.0
        assert result.in_context_benefit == pytest.approx(min(1.0, 5 * 0.15))

    def test_predict_single_context(self):
        model = InContextLearningModel(vocab_size=100, embedding_dim=8, num_heads=2)
        ctx = [([random.gauss(0, 1) for _ in range(8)], 3)]
        query = [random.gauss(0, 1) for _ in range(8)]
        result = model.predict(ctx, query)
        assert result.task_confidence == pytest.approx(result.confidence * 0.5)

    def test_predict_consistent_context(self):
        model = InContextLearningModel(vocab_size=100, embedding_dim=8, num_heads=2)
        ctx = [([random.gauss(0, 1) for _ in range(8)], 1) for _ in range(4)]
        query = [random.gauss(0, 1) for _ in range(8)]
        result = model.predict(ctx, query)
        assert 0.0 <= result.task_confidence <= 1.0


class TestTaskIdentifier:
    def test_initialization(self):
        ti = TaskIdentifier(num_tasks=5)
        assert ti.num_tasks == 5
        assert ti.task_prototypes == {}

    def test_identify_no_prototypes(self):
        ti = TaskIdentifier(num_tasks=3)
        result = ti.identify_task([], [1.0, 0.0])
        assert result == 0

    def test_update_and_identify(self):
        ti = TaskIdentifier(num_tasks=3)
        ti.update_task_prototype(1, [1.0, 0.0, 0.0])
        ti.update_task_prototype(2, [0.0, 1.0, 0.0])
        result = ti.identify_task([], [1.0, 0.0, 0.0])
        assert result == 1

    def test_update_ema(self):
        ti = TaskIdentifier(num_tasks=2)
        ti.update_task_prototype(0, [1.0, 0.0])
        original = ti.task_prototypes[0][:]
        ti.update_task_prototype(0, [0.0, 1.0])
        assert ti.task_prototypes[0] != original
        assert abs(ti.task_prototypes[0][0] - 0.9) < 1e-6
        assert abs(ti.task_prototypes[0][1] - 0.1) < 1e-6


class TestICLDynamicsAnalyzer:
    def test_initialization(self):
        analyzer = ICLDynamicsAnalyzer()
        assert 0 in analyzer.shot_performance
        assert 10 in analyzer.shot_performance

    def test_record_performance(self):
        analyzer = ICLDynamicsAnalyzer()
        analyzer.record_performance(3, 0.85)
        analyzer.record_performance(3, 0.90)
        assert len(analyzer.shot_performance[3]) == 2

    def test_learning_curve_empty(self):
        analyzer = ICLDynamicsAnalyzer()
        curve = analyzer.learning_curve()
        assert len(curve) == 11
        assert all(v == 0.0 for v in curve)

    def test_learning_curve_with_data(self):
        analyzer = ICLDynamicsAnalyzer()
        analyzer.record_performance(1, 0.5)
        analyzer.record_performance(2, 0.7)
        curve = analyzer.learning_curve()
        assert curve[1] == pytest.approx(0.5)
        assert curve[2] == pytest.approx(0.7)

    def test_sensitivity_nonzero(self):
        analyzer = ICLDynamicsAnalyzer()
        for i in range(1, 11):
            analyzer.record_performance(i, i / 10.0)
        sens = analyzer.sensitivity_to_context()
        assert sens >= 0.0

    def test_sensitivity_constant(self):
        analyzer = ICLDynamicsAnalyzer()
        for i in range(0, 11):
            analyzer.record_performance(i, 0.5)
        sens = analyzer.sensitivity_to_context()
        assert sens == pytest.approx(0.0, abs=1e-9)
