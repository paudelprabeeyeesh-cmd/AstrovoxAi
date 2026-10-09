import pytest

from quantization.mixed_precision import (
    LayerPrecisionConfig,
    MixedPrecisionConfig,
    assign_precision_by_sensitivity,
    estimate_mixed_precision_cost,
)


class TestAssignPrecisionBySensitivity:
    def test_high_sensitivity_gets_max_bits(self):
        sensitivities = {"layer1": 0.9, "layer2": 0.3}
        configs = assign_precision_by_sensitivity(sensitivities, [4, 8, 16])
        layer1 = next(c for c in configs if c.layer_name == "layer1")
        assert layer1.n_bits == 16

    def test_low_sensitivity_gets_min_bits(self):
        sensitivities = {"layer1": 0.2}
        configs = assign_precision_by_sensitivity(sensitivities, [4, 8, 16])
        assert configs[0].n_bits == 4

    def test_empty_sensitivities(self):
        configs = assign_precision_by_sensitivity({}, [4, 8, 16])
        assert configs == []

    def test_invalid_available_bits_raises(self):
        with pytest.raises(ValueError):
            assign_precision_by_sensitivity({"l": 0.5}, [])


class TestEstimateMixedPrecisionCost:
    def test_basic_cost(self):
        configs = [
            LayerPrecisionConfig("l1", 8),
            LayerPrecisionConfig("l2", 4),
        ]
        cost = estimate_mixed_precision_cost(configs, 1000)
        assert cost == pytest.approx(1000 * 6.0 / 8.0)

    def test_empty_cost(self):
        cost = estimate_mixed_precision_cost([], 1000)
        assert cost == 0.0
