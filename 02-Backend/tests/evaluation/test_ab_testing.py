from evaluation.ab_testing import VariantConfig, VariantResult, ABTest


def test_variant_config_to_dict():
    config = VariantConfig(name="control", weight=0.4, metadata={"env": "prod"})
    result = config.to_dict()
    assert result["name"] == "control"
    assert result["weight"] == 0.4
    assert result["metadata"] == {"env": "prod"}


def test_variant_result_conversion_rate():
    result = VariantResult(variant_name="a", impressions=100, conversions=25)
    assert result.conversion_rate() == 0.25


def test_variant_result_conversion_rate_zero_impressions():
    result = VariantResult(variant_name="a", impressions=0, conversions=0)
    assert result.conversion_rate() == 0.0


def test_variant_result_mean_and_std():
    result = VariantResult(variant_name="a", impressions=10, conversions=2, values=[1.0, 2.0, 3.0])
    assert result.mean_value() == 2.0
    assert result.std_value() > 0.0


def test_variant_result_mean_empty_values():
    result = VariantResult(variant_name="a", impressions=10, conversions=2)
    assert result.mean_value() == 0.0
    assert result.std_value() == 0.0


def test_ab_test_get_variant():
    ab = ABTest(name="test", variants=[VariantConfig(name="a"), VariantConfig(name="b")])
    assert ab.get_variant("a") is not None
    assert ab.get_variant("c") is None


def test_ab_test_record_impression_and_conversion():
    ab = ABTest(name="test", variants=[VariantConfig(name="a"), VariantConfig(name="b")])
    ab.record_impression("a")
    ab.record_conversion("a", value=1.0)
    result_a = ab.get_result("a")
    assert result_a.impressions == 1
    assert result_a.conversions == 1
    assert result_a.values == [1.0]


def test_ab_test_results_structure():
    ab = ABTest(name="test", variants=[VariantConfig(name="a"), VariantConfig(name="b")])
    ab.record_impression("a")
    ab.record_impression("b")
    ab.record_conversion("a")
    output = ab.results()
    assert output["test_name"] == "test"
    assert "a" in output["variants"]
    assert "comparison" in output


def test_ab_test_compare_single_variant():
    ab = ABTest(name="test", variants=[VariantConfig(name="a")])
    comparison = ab._compare_variants()
    assert comparison["winner"] is None
    assert comparison["p_value"] is None
    assert comparison["significant"] is False


def test_ab_test_run_returns_results():
    ab = ABTest(name="test", variants=[VariantConfig(name="a"), VariantConfig(name="b")])
    output = ab.run(hours=0.0)
    assert "variants" in output
    assert "comparison" in output


def test_ab_test_add_sample_data():
    ab = ABTest(name="test", variants=[VariantConfig(name="a")])
    ab.add_sample_data("a", [0.1, 0.2, 0.3])
    result = ab.get_result("a")
    assert result.impressions == 3
    assert len(result.values) == 3


def test_ab_test_minimum_sample_size():
    ab = ABTest(name="test", variants=[VariantConfig(name="a")])
    size = ab.minimum_sample_size(baseline_rate=0.1, mde=0.02, alpha=0.05, power=0.8)
    assert isinstance(size, int)
    assert size > 0


def test_ab_test_t_test_insufficient_data():
    ab = ABTest(name="test", variants=[VariantConfig(name="a"), VariantConfig(name="b")])
    ab.add_sample_data("a", [1.0])
    ab.add_sample_data("b", [2.0])
    result = ab.t_test("a", "b")
    assert result["t_statistic"] is None
    assert result["p_value"] is None
    assert result["significant"] is False
