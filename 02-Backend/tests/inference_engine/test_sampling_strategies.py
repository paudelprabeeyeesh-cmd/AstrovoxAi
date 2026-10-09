import numpy as np

from inference_engine.sampling_strategies import (
    softmax,
    log_softmax,
    greedy_sample,
    temperature_sample,
    top_k_sample,
    top_p_sample,
    min_p_sample,
    tfs_sample,
    eta_sampling,
    SamplingStrategy,
    TemperatureStrategy,
    TopKStrategy,
    TopPStrategy,
    MinPStrategy,
    TFSStrategy,
    EtaStrategy,
)


def test_softmax():
    x = np.array([[1.0, 2.0, 3.0]])
    probs = softmax(x)
    assert abs(probs.sum() - 1.0) < 1e-5
    assert probs.shape == (1, 3)


def test_log_softmax():
    x = np.array([[1.0, 2.0, 3.0]])
    log_probs = log_softmax(x)
    assert log_probs.shape == (1, 3)
    assert abs(np.exp(log_probs).sum() - 1.0) < 1e-5


def test_greedy_sample():
    probs = np.array([0.1, 0.7, 0.2])
    log_probs = np.zeros(3, dtype=np.float32)
    token = greedy_sample(probs, log_probs)
    assert token == 1


def test_temperature_sample():
    probs = np.array([0.1, 0.7, 0.2])
    log_probs = np.zeros(3, dtype=np.float32)
    rng = np.random.default_rng(42)
    token = temperature_sample(probs, log_probs, rng)
    assert token in [0, 1, 2]


def test_top_k_sample():
    probs = np.array([0.1, 0.7, 0.2])
    log_probs = np.zeros(3, dtype=np.float32)
    rng = np.random.default_rng(42)
    token = top_k_sample(probs, log_probs, k=2, rng=rng)
    assert token in [1, 2]


def test_top_p_sample():
    probs = np.array([0.1, 0.7, 0.2])
    log_probs = np.zeros(3, dtype=np.float32)
    rng = np.random.default_rng(42)
    token = top_p_sample(probs, log_probs, top_p=0.9, rng=rng)
    assert token in [0, 1, 2]


def test_min_p_sample():
    probs = np.array([0.1, 0.7, 0.2])
    log_probs = np.zeros(3, dtype=np.float32)
    rng = np.random.default_rng(42)
    token = min_p_sample(probs, log_probs, min_p=0.05, rng=rng)
    assert token in [0, 1, 2]


def test_tfs_sample():
    probs = np.array([0.1, 0.7, 0.2])
    log_probs = np.zeros(3, dtype=np.float32)
    rng = np.random.default_rng(42)
    token = tfs_sample(probs, log_probs, tfs=0.9, rng=rng)
    assert token in [0, 1, 2]


def test_eta_sampling():
    probs = np.array([0.1, 0.7, 0.2])
    log_probs = np.zeros(3, dtype=np.float32)
    rng = np.random.default_rng(42)
    token = eta_sampling(probs, log_probs, eta=0.1, rng=rng)
    assert token in [0, 1, 2]


def test_sampling_strategy_defaults():
    s = SamplingStrategy()
    assert s.temperature == 1.0
    assert s.top_k == 0
    assert s.top_p == 1.0


def test_sampling_strategy_configure():
    s = SamplingStrategy(temperature=1.0, top_k=50)
    s.configure(temperature=0.5, top_k=20)
    assert s.temperature == 0.5
    assert s.top_k == 20


def test_sampling_strategy_sample():
    s = SamplingStrategy(seed=42)
    logits = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    token = s.sample(logits)
    assert token in [0, 1, 2]


def test_sampling_strategy_sample_with_log_probs():
    s = SamplingStrategy(seed=42)
    logits = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    result = s.sample(logits, return_log_probs=True)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert result[0] in [0, 1, 2]


def test_sampling_strategy_get_all_hyperparameters():
    s = SamplingStrategy(temperature=0.5, top_k=50)
    hp = s.get_all_hyperparameters()
    assert hp["temperature"] == 0.5
    assert hp["top_k"] == 50


def test_temperature_strategy():
    s = TemperatureStrategy(temperature=2.0)
    logits = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    token = s.sample(logits)
    assert token in [0, 1, 2]


def test_top_k_strategy():
    s = TopKStrategy(k=2)
    logits = np.array([1.0, 5.0, 3.0], dtype=np.float32)
    token = s.sample(logits)
    assert token in [1, 2]


def test_top_p_strategy():
    s = TopPStrategy(p=0.9)
    logits = np.array([1.0, 5.0, 3.0], dtype=np.float32)
    token = s.sample(logits)
    assert token in [0, 1, 2]


def test_min_p_strategy():
    s = MinPStrategy(p=0.1)
    logits = np.array([1.0, 5.0, 3.0], dtype=np.float32)
    token = s.sample(logits)
    assert token in [0, 1, 2]


def test_tfs_strategy():
    s = TFSStrategy(tfs=0.9)
    logits = np.array([1.0, 5.0, 3.0], dtype=np.float32)
    token = s.sample(logits)
    assert token in [0, 1, 2]


def test_eta_strategy():
    s = EtaStrategy(eta=0.1)
    logits = np.array([1.0, 5.0, 3.0], dtype=np.float32)
    token = s.sample(logits)
    assert token in [0, 1, 2]


def test_sampling_strategy_invalid_temperature():
    s = SamplingStrategy()
    try:
        s.sample(np.array([1.0, 2.0, 3.0], dtype=np.float32))
    except ValueError:
        pass


def test_greedy_sample_with_log_probs():
    probs = np.array([0.1, 0.7, 0.2])
    log_probs = np.zeros(3, dtype=np.float32)
    result = greedy_sample(probs, log_probs, return_log_probs=True)
    assert isinstance(result, tuple)
    assert result[0] in [0, 1, 2]


def test_sampling_strategy_get_hyperparameters():
    s = TopPStrategy(p=0.95, temperature=0.5, seed=123)
    hp = s.get_all_hyperparameters()
    assert hp["strategy_type"] == "top_p"
    assert hp["temperature"] == 0.5
    assert hp["seed"] == 123
