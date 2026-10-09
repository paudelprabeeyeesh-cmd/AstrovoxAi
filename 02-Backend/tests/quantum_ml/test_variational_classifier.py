import numpy as np
import pytest
from quantum_ml.quantum_circuits import QuantumCircuit
from quantum_ml.variational_classifier import VariationalClassifier


class TestVariationalClassifier:
    def test_fit_predict_shape(self):
        X = np.random.randn(20, 3)
        y = np.array([1] * 10 + [0] * 10)
        clf = VariationalClassifier(num_qubits=3, num_layers=2)
        clf.fit(X, y, epochs=5, lr=0.01)
        preds = np.array([clf.predict(x) for x in X])
        assert preds.shape == (20,)

    def test_predict_labels(self):
        X = np.random.randn(20, 3)
        y = np.array([1] * 10 + [0] * 10)
        clf = VariationalClassifier(num_qubits=3, num_layers=2)
        clf.fit(X, y, epochs=5, lr=0.01)
        preds = np.array([clf.predict(x) for x in X])
        assert set(np.unique(preds)).issubset({0, 1})

    def test_predict_proba_range(self):
        X = np.random.randn(10, 3)
        clf = VariationalClassifier(num_qubits=3, num_layers=2)
        clf.fit(X, np.array([1] * 5 + [0] * 5), epochs=5, lr=0.01)
        for x in X:
            p = clf.predict_proba(x)
            assert 0 <= p <= 1

    def test_fit_returns_self(self):
        clf = VariationalClassifier(num_qubits=2, num_layers=2)
        X = np.random.randn(5, 2)
        y = np.array([1, 0, 1, 0, 1])
        result = clf.fit(X, y, epochs=2, lr=0.01)
        assert result is clf

    def test_different_params_change_prediction(self):
        X = np.random.randn(10, 2)
        clf = VariationalClassifier(num_qubits=2, num_layers=2)
        clf.fit(X, np.array([1] * 5 + [0] * 5), epochs=5, lr=0.01)
        preds1 = np.array([clf.predict_proba(x) for x in X])
        clf.params = np.random.randn(*clf.params.shape) * 10
        preds2 = np.array([clf.predict_proba(x) for x in X])
        assert not np.allclose(preds1, preds2)

    def test_predict_single_feature(self):
        clf = VariationalClassifier(num_qubits=1, num_layers=1)
        X = np.array([[0.5], [0.6]])
        y = np.array([1, 0])
        clf.fit(X, y, epochs=5, lr=0.01)
        pred = clf.predict(np.array([0.5]))
        assert pred in {0, 1}


class TestVariationalClassifierMethods:
    def test_ansatz_returns_circuit(self):
        clf = VariationalClassifier(num_qubits=2, num_layers=2)
        x = np.random.randn(2)
        params = np.random.randn(clf.num_layers * clf.num_qubits * 2)
        circuit = clf._ansatz(x, params)
        assert isinstance(circuit, QuantumCircuit)
        assert circuit.num_qubits == 2

    def test_loss_computes_mse(self):
        clf = VariationalClassifier(num_qubits=2, num_layers=2)
        X = np.random.randn(5, 2)
        y = np.array([1, 0, 1, 0, 1])
        loss = clf._loss(X, y, clf.params)
        assert isinstance(loss, float)
        assert loss >= 0

    def test_gradient_shape(self):
        clf = VariationalClassifier(num_qubits=2, num_layers=2)
        X = np.random.randn(5, 2)
        y = np.array([1, 0, 1, 0, 1])
        grad = clf._gradient(X, y, clf.params)
        assert grad.shape == clf.params.shape
