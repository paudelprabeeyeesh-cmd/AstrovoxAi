from learning_to_learn.transfer_prior import TransferPrior, Prior


def test_prior_creation():
    prior = Prior(source_task_id="t1", parameters={"p": 0.5})
    assert prior.source_task_id == "t1"
    assert prior.parameters == {"p": 0.5}
    assert prior.confidence == 1.0


def test_transfer_prior_register():
    tp = TransferPrior()
    tp.register_prior("t1", {"p": 0.5}, confidence=0.8)
    assert "t1" in tp.priors
    assert tp.priors["t1"].confidence == 0.8


def test_transfer_prior_suggest_no_priors():
    tp = TransferPrior()
    assert tp.suggest({"f1": 0.5}) is None


def test_transfer_prior_suggest_best():
    tp = TransferPrior()
    tp.register_prior("t1", {"p": 0.9})
    tp.register_prior("t2", {"p": 0.1})
    result = tp.suggest({"p": 0.9})
    assert result is not None
    assert result["p"] == 0.9


def test_transfer_prior_suggest_low_similarity():
    tp = TransferPrior()
    tp.register_prior("t1", {"p": 0.9})
    result = tp.suggest({"q": 0.5})
    assert result is None


def test_transfer_prior_transfer():
    tp = TransferPrior()
    tp.register_prior("t1", {"p": 0.8})
    result = tp.transfer("t1", "t2", 0.5)
    assert result == {"p": 0.4}
    assert len(tp.transfer_history) == 1
    assert tp.transfer_history[0]["source"] == "t1"
    assert tp.transfer_history[0]["target"] == "t2"


def test_transfer_prior_transfer_missing_source():
    tp = TransferPrior()
    try:
        tp.transfer("missing", "t2", 0.5)
    except KeyError:
        pass
    else:
        raise AssertionError("Expected KeyError")


def test_transfer_prior_decay():
    tp = TransferPrior()
    tp.register_prior("t1", {"p": 0.8}, confidence=0.9)
    tp.decay("t1", 0.5)
    assert tp.priors["t1"].confidence == 0.45
    assert tp.priors["t1"].parameters["p"] == 0.4


def test_transfer_prior_decay_missing():
    tp = TransferPrior()
    try:
        tp.decay("missing", 0.5)
    except KeyError:
        pass
    else:
        raise AssertionError("Expected KeyError")


def test_transfer_prior_get_confidence():
    tp = TransferPrior()
    tp.register_prior("t1", {"p": 0.8}, confidence=0.9)
    assert tp.get_confidence("t1") == 0.9


def test_transfer_prior_get_confidence_missing():
    tp = TransferPrior()
    try:
        tp.get_confidence("missing")
    except KeyError:
        pass
    else:
        raise AssertionError("Expected KeyError")


def test_transfer_prior_similarity_identical():
    tp = TransferPrior()
    similarity = tp._compute_similarity({"p": 0.5}, {"p": 0.5})
    assert similarity == 1.0


def test_transfer_prior_similarity_no_shared_keys():
    tp = TransferPrior()
    similarity = tp._compute_similarity({"p": 0.5}, {"q": 0.5})
    assert similarity == 0.0


def test_transfer_prior_similarity_partial():
    tp = TransferPrior()
    similarity = tp._compute_similarity({"p": 0.5}, {"p": 0.7})
    assert similarity < 1.0
    assert similarity > 0.0
