import numpy as np
from advanced_optimization.surrogate_model import RBFSurrogate, PolynomialSurrogate


def test_rbf_surrogate_fit_predict():
    x_train = np.array([[0.0], [1.0], [2.0], [3.0]])
    y_train = np.array([0.0, 1.0, 4.0, 9.0])
    model = RBFSurrogate(length_scale=1.0, noise=1e-6)
    model.fit(x_train, y_train)
    mean, var = model.predict(np.array([1.5]))
    assert isinstance(mean, float) or mean.size == 1
    assert isinstance(var, float) or var.size == 1


def test_polynomial_surrogate_fit_predict():
    x_train = np.array([[0.0], [1.0], [2.0], [3.0]])
    y_train = x_train[:, 0] ** 2
    model = PolynomialSurrogate(degree=2)
    model.fit(x_train, y_train)
    preds = model.predict(np.array([[1.5], [2.5]]))
    assert preds.shape == (2,)
    assert np.allclose(preds, [1.5 ** 2, 2.5 ** 2], atol=0.5)
