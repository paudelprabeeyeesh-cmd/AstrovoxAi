from metacognition.uncertainty_quantifier import UncertaintyQuantifier, UncertaintyEstimate


def test_record_prediction():
    uq = UncertaintyQuantifier()
    uq.record_prediction("key1", 0.9)
    assert "key1" in uq.uncertainty_history


def test_aleatoric():
    uq = UncertaintyQuantifier()
    probs = [0.7, 0.3]
    aleatoric = uq.aleatoric(probs)
    assert aleatoric > 0.0


def test_epistemic():
    uq = UncertaintyQuantifier()
    probs = [0.7, 0.3]
    epistemic = uq.epistemic(probs)
    assert epistemic >= 0.0


def test_entropy():
    uq = UncertaintyQuantifier()
    probs = [0.7, 0.3]
    ent = uq.entropy(probs)
    assert ent > 0.0


def test_quantify():
    uq = UncertaintyQuantifier()
    probs = [0.7, 0.3]
    est = uq.quantify("key1", probs)
    assert est.total > 0.0
    assert est.entropy > 0.0


def test_variance_estimate():
    uq = UncertaintyQuantifier()
    uq.record_prediction("key1", 0.8)
    var = uq.variance_estimate("key1", 0.8)
    assert var > 0.0


def test_variance_estimate_no_history():
    uq = UncertaintyQuantifier()
    var = uq.variance_estimate("key1", 0.8)
    assert var > 0.0


def test_mutual_information():
    uq = UncertaintyQuantifier()
    distributions = [[0.7, 0.3], [0.5, 0.5]]
    mi = uq.mutual_information(distributions)
    assert mi >= 0.0


def test_mutual_information_empty():
    uq = UncertaintyQuantifier()
    mi = uq.mutual_information([])
    assert mi == 0.0


def test_sensitivity_analysis():
    uq = UncertaintyQuantifier()
    uq.record_prediction("key1", 0.8)
    uq.record_prediction("key1", 0.7)
    sa = uq.sensitivity_analysis("key1", perturbation=0.1)
    assert sa >= 0.0


def test_sensitivity_analysis_no_history():
    uq = UncertaintyQuantifier()
    sa = uq.sensitivity_analysis("key1")
    assert sa == 0.0


def test_class_uncertainty():
    uq = UncertaintyQuantifier()
    uq.record_class_sample("key1", "cls1", 0.8)
    uq.record_class_sample("key1", "cls1", 0.9)
    result = uq.class_uncertainty("key1")
    assert "cls1" in result


def test_class_uncertainty_no_history():
    uq = UncertaintyQuantifier()
    result = uq.class_uncertainty("key1")
    assert result == {}


def test_record_class_sample():
    uq = UncertaintyQuantifier()
    uq.record_class_sample("key1", "cls1", 0.8)
    assert "key1" in uq.class_histories
    assert "cls1" in uq.class_histories["key1"]


def test_quantify_records_history():
    uq = UncertaintyQuantifier()
    uq.quantify("key1", [0.7, 0.3])
    assert "key1" in uq.uncertainty_history
    assert len(uq.uncertainty_history["key1"]) == 1


def test_aleatoric_uniform():
    uq = UncertaintyQuantifier()
    probs = [0.5, 0.5]
    aleatoric = uq.aleatoric(probs)
    assert aleatoric > 0.0


def test_entropy_single_probability():
    uq = UncertaintyQuantifier()
    probs = [1.0]
    ent = uq.entropy(probs)
    assert ent == 0.0


def test_entropy_clamped():
    uq = UncertaintyQuantifier()
    probs = [0.0, 1.0]
    ent = uq.entropy(probs)
    assert ent >= 0.0


def test_quantify_total_capped():
    uq = UncertaintyQuantifier()
    probs = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
    est = uq.quantify("key1", probs)
    assert est.total <= 1.0


def test_variance_estimate_empty_history():
    uq = UncertaintyQuantifier()
    var = uq.variance_estimate("key1", 0.8)
    assert var > 0.0


def test_mutual_information_single_distribution():
    uq = UncertaintyQuantifier()
    mi = uq.mutual_information([[0.7, 0.3]])
    assert mi >= 0.0


def test_sensitivity_analysis_fewer_than_10():
    uq = UncertaintyQuantifier()
    uq.record_prediction("key1", 0.8)
    sa = uq.sensitivity_analysis("key1", perturbation=0.1)
    assert sa >= 0.0


def test_class_uncertainty_no_samples_for_class():
    uq = UncertaintyQuantifier()
    uq.record_class_sample("key1", "cls1", 0.8)
    result = uq.class_uncertainty("key1")
    assert "cls1" in result
    assert result["cls1"] >= 0.0


def test_record_class_sample_multiple_classes():
    uq = UncertaintyQuantifier()
    uq.record_class_sample("key1", "cls1", 0.8)
    uq.record_class_sample("key1", "cls2", 0.6)
    assert len(uq.class_histories["key1"]) == 2
