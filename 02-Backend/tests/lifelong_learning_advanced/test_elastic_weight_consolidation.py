import numpy as np

from lifelong_learning_advanced.elastic_weight_consolidation import ElasticWeightConsolidation, EWCConfig


class TestElasticWeightConsolidation:
    def _simple_forward(self, x, params):
        h = np.maximum(x @ params["W1"] + params["b1"], 0)
        return h @ params["W2"] + params["b2"]

    def test_default_config(self):
        ewc = ElasticWeightConsolidation()
        assert ewc.config.lambda_val == 100.0

    def test_custom_config(self):
        ewc = ElasticWeightConsolidation(config=EWCConfig(lambda_val=10.0))
        assert ewc.config.lambda_val == 10.0

    def test_register_params(self):
        ewc = ElasticWeightConsolidation()
        params = {
            "W1": np.random.randn(4, 8),
            "b1": np.zeros(8),
            "W2": np.random.randn(8, 2),
            "b2": np.zeros(2),
        }
        ewc.register_params(params)
        assert len(ewc.fisher) == 4

    def test_compute_fisher(self):
        ewc = ElasticWeightConsolidation()
        params = {
            "W1": np.random.randn(4, 8),
            "b1": np.zeros(8),
            "W2": np.random.randn(8, 2),
            "b2": np.zeros(2),
        }
        x = np.random.randn(10, 4)
        ewc.compute_fisher(params, x, self._simple_forward)
        for v in ewc.fisher.values():
            assert np.all(v >= 0)

    def test_update_prev_params(self):
        ewc = ElasticWeightConsolidation()
        params = {"W1": np.ones((2, 2)), "b1": np.zeros(2)}
        ewc.register_params(params)
        ewc.update_prev_params(params)
        assert np.allclose(ewc.prev_params["W1"], np.ones((2, 2)))

    def test_penalty(self):
        ewc = ElasticWeightConsolidation(config=EWCConfig(lambda_val=1.0))
        params = {
            "W1": np.ones((2, 2)),
            "b1": np.zeros(2),
            "W2": np.ones((2, 2)),
            "b2": np.zeros(2),
        }
        ewc.register_params(params)
        ewc.update_prev_params(params)
        ewc.fisher["W1"] = np.ones((2, 2))
        penalty = ewc.penalty(params)
        assert penalty >= 0.0

    def test_get_report(self):
        ewc = ElasticWeightConsolidation()
        report = ewc.get_report()
        assert "lambda" in report
        assert "num_params" in report
        assert "fisher_norms" in report
