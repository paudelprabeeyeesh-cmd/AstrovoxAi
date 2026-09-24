import numpy as np
import pytest
from quantum_ml.quantum_advantage import QuantumSupremacyBenchmark, QuantumAdvantageTest


class TestQuantumSupremacyBenchmark:
    def test_random_circuit_sampling_shape(self):
        circuit = QuantumSupremacyBenchmark.random_circuit_sampling(num_qubits=4, depth=3)
        assert circuit.num_qubits == 4

    def test_compute_heavy_outputs(self):
        state = np.array([0.5, 0.3, 0.2, 0.1])
        probs = np.abs(state)**2
        heavy = QuantumSupremacyBenchmark.compute_heavy_outputs(probs, fraction=0.5)
        assert len(heavy) == 2

    def test_cross_entropy_benchmark(self):
        counts = {"00": 50, "01": 30, "10": 15, "11": 5}
        heavy = [0, 1]
        ce = QuantumSupremacyBenchmark.cross_entropy_benchmark(counts, heavy, num_qubits=2)
        assert ce >= 0

    def test_quantum_volume(self):
        qv = QuantumSupremacyBenchmark.quantum_volume(num_qubits=3, depth=2, trials=3)
        assert 0 <= qv <= 1


class TestQuantumAdvantageTest:
    def test_benchmark_linear_algebra(self):
        bench = QuantumAdvantageTest()
        result = bench.benchmark_linear_algebra(10)
        assert "size" in result
        assert result["size"] == 10

    def test_benchmark_optimization(self):
        bench = QuantumAdvantageTest()
        result = bench.benchmark_optimization(4, trials=2)
        assert "n" in result
        assert result["n"] == 4

    def test_benchmark_kernel_method(self):
        bench = QuantumAdvantageTest()
        result = bench.benchmark_kernel_method(10, 3)
        assert "samples" in result
