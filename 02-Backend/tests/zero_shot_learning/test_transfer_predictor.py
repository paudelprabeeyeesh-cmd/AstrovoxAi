from zero_shot_learning.transfer_predictor import TransferPredictor, SourceExample, TargetExample


def test_predict_basic():
    predictor = TransferPredictor()
    predictor.add_source([
        SourceExample(features=[1.0, 0.0], label="A"),
        SourceExample(features=[0.8, 0.2], label="A"),
        SourceExample(features=[0.0, 1.0], label="B"),
        SourceExample(features=[0.2, 0.8], label="B"),
    ])
    target = TargetExample(features=[0.9, 0.1])
    pred, score = predictor.predict(target)
    assert pred == "A"
    assert score > 0


def test_predict_not_fitted():
    predictor = TransferPredictor()
    target = TargetExample(features=[1.0, 0.0])
    try:
        predictor.predict(target)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected RuntimeError")


def test_evaluate():
    predictor = TransferPredictor()
    predictor.add_source([
        SourceExample(features=[1.0, 0.0], label="A"),
        SourceExample(features=[0.0, 1.0], label="B"),
    ])
    targets = [
        TargetExample(features=[0.9, 0.1], true_label="A"),
        TargetExample(features=[0.1, 0.9], true_label="B"),
    ]
    report = predictor.evaluate(targets)
    assert report["count"] == 2
    assert report["accuracy"] == 1.0


def test_get_report():
    predictor = TransferPredictor()
    predictor.add_source([SourceExample(features=[1.0], label="X")])
    report = predictor.get_report()
    assert report["source_count"] == 1
    assert report["fitted"] is True
    assert "X" in report["classes"]
