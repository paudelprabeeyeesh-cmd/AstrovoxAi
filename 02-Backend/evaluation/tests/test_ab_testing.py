from evaluation.ab_testing import (
    ABTest,
    VariantConfig,
    VariantResult,
)


def test_variant_result_conversion_rate():
    result = VariantResult(variant_name="a", impressions=100, conversions=10)
    assert result.conversion_rate() == 0.1


def test_variant_result_conversion_rate_zero_impressions():
    result = VariantResult(variant_name="a", impressions=0, conversions=0)
    assert result.conversion_rate() == 0.0


def test_variant_result_mean_std():
    result = VariantResult(variant_name="a", impressions=0, conversions=0, values=[1.0, 2.0, 3.0])
    assert result.mean_value() == 2.0
    assert result.std_value() > 0.0


def test_variant_result_mean_std_empty():
    result = VariantResult(variant_name="a", impressions=0, conversions=0)
    assert result.mean_value() == 0.0
    assert result.std_value() == 0.0


def test_ab_test_basic_flow():
    variants = [VariantConfig(name="control"), VariantConfig(name="treatment")]
    test = ABTest(name="t1", variants=variants)
    test.record_impression("control")
    test.record_impression("control")
    test.record_conversion("control", 1.0)
    test.record_impression("treatment")
    test.record_conversion("treatment", 2.0)
    results = test.results()
    assert results["test_name"] == "t1"
    assert "comparison" in results


def test_ab_test_single_variant():
    variants = [VariantConfig(name="control")]
    test = ABTest(name="t1", variants=variants)
    results = test.results()
    assert results["comparison"]["winner"] is None


def test_ab_test_t_test_insufficient_data():
    variants = [VariantConfig(name="a"), VariantConfig(name="b")]
    test = ABTest(name="t1", variants=variants)
    result = test.t_test("a", "b")
    assert result["t_statistic"] is None
    assert result["p_value"] is None


def test_ab_test_minimum_sample_size():
    variants = [VariantConfig(name="a")]
    test = ABTest(name="t1", variants=variants)
    size = test.minimum_sample_size(baseline_rate=0.1, mde=0.05)
    assert isinstance(size, int)
    assert size >= 0
