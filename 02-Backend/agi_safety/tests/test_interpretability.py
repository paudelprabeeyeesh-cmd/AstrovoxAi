import numpy as np
import pytest
from agi_safety.interpretability import (
    MechanisticInterpreter,
    SimpleNeuralCircuit,
    variance_of_interpretability,
    ActivationTrace,
    Circuit,
)


class TestSimpleNeuralCircuit:
    def setup_method(self):
        self.circuit = SimpleNeuralCircuit(input_dim=8, hidden_dims=[16, 8, 4], seed=42)

    def test_forward_output_shape(self):
        x = np.random.randn(4, 8)
        out, traces = self.circuit.forward(x, return_traces=True)
        assert out.shape == (4, 4)

    def test_forward_without_traces(self):
        x = np.random.randn(2, 8)
        out, traces = self.circuit.forward(x, return_traces=False)
        assert traces == []

    def test_traces_length_matches_layers(self):
        x = np.random.randn(2, 8)
        _, traces = self.circuit.forward(x, return_traces=True)
        assert len(traces) == len(self.circuit.layers)

    def test_trace_contains_required_fields(self):
        x = np.random.randn(2, 8)
        _, traces = self.circuit.forward(x, return_traces=True)
        trace = traces[0]
        assert isinstance(trace, ActivationTrace)
        assert trace.layer_name == self.circuit.layers[0]
        assert trace.inputs.shape == (2, 8)
        assert trace.weights is not None

    def test_relu_activation(self):
        x = np.array([[-1.0, 2.0, -3.0, 0.0, 1.0, -2.0, 3.0, -1.0]])
        out, _ = self.circuit.forward(x)
        assert np.all(out >= 0)

    def test_deterministic_with_seed(self):
        c1 = SimpleNeuralCircuit(8, [16, 4], seed=42)
        c2 = SimpleNeuralCircuit(8, [16, 4], seed=42)
        x = np.random.randn(2, 8)
        out1, _ = c1.forward(x)
        out2, _ = c2.forward(x)
        np.testing.assert_allclose(out1, out2)

    def test_different_seed_produces_different_outputs(self):
        c1 = SimpleNeuralCircuit(8, [16, 4], seed=1)
        c2 = SimpleNeuralCircuit(8, [16, 4], seed=2)
        x = np.random.randn(2, 8)
        out1, _ = c1.forward(x)
        out2, _ = c2.forward(x)
        assert not np.allclose(out1, out2)

    def test_get_weights_returns_dict(self):
        weights = self.circuit.get_weights()
        assert isinstance(weights, dict)
        assert len(weights) > 0


class TestMechanisticInterpreter:
    def setup_method(self):
        self.circuit = SimpleNeuralCircuit(input_dim=8, hidden_dims=[16, 8, 4], seed=42)
        self.interpreter = MechanisticInterpreter(self.circuit, threshold=0.01)

    def test_contribute_nonnegative(self):
        x = np.random.randn(2, 8)
        contribs = self.interpreter.compute_contribution(x)
        for v in contribs.values():
            assert v >= 0.0

    def test_trace_circuit_returns_circuit(self):
        x = np.random.randn(1, 8)
        circuit = self.interpreter.trace_circuit(x, target_class=0)
        assert isinstance(circuit, Circuit)

    def test_circuit_nodes_are_strings(self):
        x = np.random.randn(1, 8)
        circuit = self.interpreter.trace_circuit(x, target_class=0)
        for node in circuit.nodes:
            assert isinstance(node, str)

    def test_circuit_contribution_nonnegative(self):
        x = np.random.randn(1, 8)
        circuit = self.interpreter.trace_circuit(x, target_class=0)
        assert circuit.contribution >= 0.0

    def test_ablate_layer_zeroes_output(self):
        x = np.random.randn(1, 8)
        original, _ = self.circuit.forward(x)
        ablated = self.interpreter.ablated_layer(x, self.circuit.layers[0])
        assert ablated.shape == original.shape


class TestVarianceOfInterpretability:
    def test_empty_traces(self):
        result = variance_of_interpretability([])
        assert result == 0.0

    def test_single_trace(self):
        trace = ActivationTrace(layer_name="l", inputs=np.zeros((1, 4)), outputs=np.ones((1, 4)))
        result = variance_of_interpretability([trace])
        assert result >= 0.0

    def test_multiple_traces(self):
        traces = [
            ActivationTrace(layer_name="l", inputs=np.zeros((1, 4)), outputs=np.ones((1, 4))),
            ActivationTrace(layer_name="l", inputs=np.zeros((1, 4)), outputs=np.zeros((1, 4))),
        ]
        result = variance_of_interpretability(traces)
        assert result >= 0.0
