import numpy as np
import pytest
from ..elastic_weight_consolidation import (
    ElasticWeightConsolidation,
    FisherStatistics
)


class TestElasticWeightConsolidation:
    def test_initialization(self):
        ewc = ElasticWeightConsolidation(ewc_lambda=100.0, fisher_sample_size=1000)
        assert ewc.ewc_lambda == 100.0
        assert ewc.fisher_sample_size == 1000
        assert len(ewc.consolidated_layers) == 0

    def test_consolidate_with_samples(self):
        ewc = ElasticWeightConsolidation()
        state = {"layer1": np.array([1.0, 2.0, 3.0])}
        samples = [
            {"layer1": np.array([1.0, 2.0, 3.0])},
            {"layer1": np.array([2.0, 3.0, 4.0])},
            {"layer1": np.array([3.0, 4.0, 5.0])}
        ]

        ewc.consolidate_task("task1", state, samples=samples)

        assert "task1" in ewc.task_fisher_history
        assert "layer1" in ewc.consolidated_layers
        assert len(ewc.consolidated_layers) == 1

    def test_consolidate_without_samples_or_gradients_raises(self):
        ewc = ElasticWeightConsolidation()
        state = {"layer1": np.array([1.0, 2.0])}
        with pytest.raises(ValueError, match="Must provide either samples or gradients"):
            ewc.consolidate_task("task1", state)

    def test_compute_fisher_from_samples(self):
        ewc = ElasticWeightConsolidation()
        samples = [
            {"layer1": np.array([1.0, 2.0])},
            {"layer1": np.array([2.0, 4.0])},
            {"layer1": np.array([3.0, 6.0])}
        ]

        fisher = ewc.compute_fisher_from_samples(samples)
        expected = np.array([4.6667, 18.6667])
        assert np.allclose(fisher["layer1"], expected, atol=0.001)

    def test_compute_fisher_empty_samples(self):
        ewc = ElasticWeightConsolidation()
        fisher = ewc.compute_fisher_from_samples([])
        assert fisher == {}

    def test_compute_penalty(self):
        ewc = ElasticWeightConsolidation(ewc_lambda=1.0)
        state = {"layer1": np.array([1.0, 2.0])}
        ewc.consolidate_task("task1", state, samples=[{"layer1": state["layer1"]}])

        new_state = {"layer1": np.array([1.5, 1.5])}
        penalty = ewc.compute_penalty(new_state)
        assert penalty > 0

    def test_compute_penalty_zero_when_optimal(self):
        ewc = ElasticWeightConsolidation(ewc_lambda=1.0)
        state = {"layer1": np.array([1.0, 2.0])}
        ewc.consolidate_task("task1", state, samples=[{"layer1": state["layer1"]}])

        penalty = ewc.compute_penalty(state)
        assert np.isclose(penalty, 0.0)

    def test_get_fisher_statistics(self):
        ewc = ElasticWeightConsolidation()
        state = {"layer1": np.array([1.0, 2.0, 3.0])}
        samples = [
            {"layer1": np.array([1.0, 2.0, 3.0])},
            {"layer1": np.array([2.0, 4.0, 6.0])},
            {"layer1": np.array([3.0, 6.0, 9.0])}
        ]
        ewc.consolidate_task("task1", state, samples=samples)

        stats = ewc.get_fisher_statistics("task1")
        assert "layer1" in stats
        assert isinstance(stats["layer1"], FisherStatistics)
        assert stats["layer1"].mean_fisher > 0
        assert stats["layer1"].sparsity == 0.0

    def test_get_fisher_statistics_unknown_task(self):
        ewc = ElasticWeightConsolidation()
        stats = ewc.get_fisher_statistics("unknown")
        assert stats == {}

    def test_get_importance_ranking(self):
        ewc = ElasticWeightConsolidation()
        state = {
            "layer1": np.array([1.0]),
            "layer2": np.array([2.0]),
            "layer3": np.array([3.0])
        }
        samples = [
            {"layer1": np.array([1.0]), "layer2": np.array([2.0]), "layer3": np.array([3.0])},
            {"layer1": np.array([10.0]), "layer2": np.array([4.0]), "layer3": np.array([6.0])}
        ]
        ewc.consolidate_task("task1", state, samples=samples)

        ranking = ewc.get_importance_ranking("task1", top_k=2)
        assert len(ranking) == 2
        assert ranking[0][1] >= ranking[1][1]

    def test_get_importance_ranking_unknown_task(self):
        ewc = ElasticWeightConsolidation()
        ranking = ewc.get_importance_ranking("unknown")
        assert ranking == []

    def test_adaptive_lambda(self):
        ewc = ElasticWeightConsolidation(ewc_lambda=100.0)
        state = {"layer1": np.array([1.0, 2.0])}
        ewc.consolidate_task("task1", state, samples=[{"layer1": state["layer1"]}])

        new_state = {"layer1": np.array([1.5, 1.5])}
        adaptive = ewc.adaptive_lambda(new_state, base_lambda=100.0)

        assert adaptive > 100.0

    def test_merge_fisher_matrices_weighted_average(self):
        ewc = ElasticWeightConsolidation()
        state = {"layer1": np.array([1.0])}

        ewc.consolidate_task("task1", state, samples=[{"layer1": np.array([1.0])}])
        ewc.consolidate_task("task2", state, samples=[{"layer1": np.array([2.0])}])

        merged = ewc.merge_fisher_matrices(["task1", "task2"], method="weighted_average")
        assert "layer1" in merged
        assert np.allclose(merged["layer1"], np.array([2.5]))

    def test_merge_fisher_matrices_max(self):
        ewc = ElasticWeightConsolidation()
        state = {"layer1": np.array([1.0])}

        ewc.consolidate_task("task1", state, samples=[{"layer1": np.array([1.0])}])
        ewc.consolidate_task("task2", state, samples=[{"layer1": np.array([10.0])}])

        merged = ewc.merge_fisher_matrices(["task1", "task2"], method="max")
        assert "layer1" in merged
        assert np.allclose(merged["layer1"], np.array([100.0]))

    def test_merge_fisher_matrices_unknown_method(self):
        ewc = ElasticWeightConsolidation()
        with pytest.raises(ValueError, match="Unknown merge method"):
            ewc.merge_fisher_matrices(["task1"], method="unknown")

    def test_multiple_tasks(self):
        ewc = ElasticWeightConsolidation()
        state = {"layer1": np.array([1.0])}

        ewc.consolidate_task("task1", state, samples=[{"layer1": np.array([1.0])}])
        ewc.consolidate_task("task2", state, samples=[{"layer1": np.array([2.0])}])
        ewc.consolidate_task("task3", state, samples=[{"layer1": np.array([3.0])}])

        assert ewc.ewc_memory.task_count == 3
        assert len(ewc.task_fisher_history) == 3
