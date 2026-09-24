from advanced_security.differential_privacy import (
    DifferentialPrivacy,
    GaussianMechanism,
    LaplaceMechanism,
    SparseMechanism,
)


def test_laplace_mechanism() -> None:
    mech = LaplaceMechanism(epsilon=1.0)
    for _ in range(100):
        assert isinstance(mech.noise(), float)


def test_gaussian_mechanism() -> None:
    mech = GaussianMechanism(epsilon=0.5, delta=1e-5)
    for _ in range(100):
        assert isinstance(mech.noise(), float)


def test_differential_privacy_histogram() -> None:
    dp = DifferentialPrivacy(epsilon=1.0)
    data = [0, 1, 1, 2, 2, 2]
    histogram = dp.histogram(data, bins=3)
    assert len(histogram) == 3


def test_differential_privacy_attribute_value() -> None:
    dp = DifferentialPrivacy(epsilon=1.0)
    result = dp.attribute_value(10.0, 0.0, 100.0)
    assert result >= 0.0


def test_sparse_mechanism_noise() -> None:
    mech = SparseMechanism(epsilon=1.0, sparsity=1)
    for _ in range(100):
        noise = mech.noise()
        assert noise == 0.0 or isinstance(noise, float)


def test_differential_privacy_query_laplace() -> None:
    dp = DifferentialPrivacy(epsilon=1.0)
    result = dp.query([1.0, 2.0, 3.0], mechanism="laplace")
    assert result == (1.0 + 2.0 + 3.0)


def test_differential_privacy_query_gaussian() -> None:
    dp = DifferentialPrivacy(epsilon=0.5, delta=1e-5)
    result = dp.query([1.0, 2.0, 3.0], mechanism="gaussian")
    assert result == (1.0 + 2.0 + 3.0)


def test_differential_privacy_histogram_sum() -> None:
    dp = DifferentialPrivacy(epsilon=1.0)
    data = [0] * 10 + [1] * 5 + [2] * 5
    hist = dp.histogram(data, bins=3)
    assert len(hist) == 3
