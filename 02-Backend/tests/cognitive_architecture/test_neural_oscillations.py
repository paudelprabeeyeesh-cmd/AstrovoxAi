import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from cognitive_architecture.neural_oscillations import (
    NeuralOscillator,
    PhaseAmplitudeCoupling,
    TemporalBinding,
    NeuralOscillationsSystem,
)


class TestNeuralOscillator:
    def test_band_classification(self):
        osc = NeuralOscillator(frequency=6.0)
        assert osc.band == "theta"

    def test_sample_returns_value(self):
        osc = NeuralOscillator(frequency=10.0, amplitude=1.0, phase=0.0)
        val = osc.sample(t=0.0)
        assert val == pytest.approx(0.0)

    def test_sample_nonzero(self):
        osc = NeuralOscillator(frequency=10.0, amplitude=1.0, phase=np.pi / 2)
        val = osc.sample(t=0.0)
        assert val == pytest.approx(1.0)

    def test_update_changes_phase(self):
        osc = NeuralOscillator(frequency=10.0, phase=0.5)
        initial_phase = osc.phase
        osc.update(dt=0.1, coupling=1.0)
        assert osc.phase != initial_phase

    def test_delta_band(self):
        osc = NeuralOscillator(frequency=2.0)
        assert osc.band == "delta"

    def test_gamma_band(self):
        osc = NeuralOscillator(frequency=50.0)
        assert osc.band == "gamma"


class TestPhaseAmplitudeCoupling:
    def test_pac_returns_value(self):
        pac = PhaseAmplitudeCoupling()
        phase = np.random.randn(100)
        amplitude = np.random.randn(100)
        val = pac.compute_pac(phase, amplitude, n_bins=10)
        assert val >= 0.0

    def test_empty_signals(self):
        pac = PhaseAmplitudeCoupling()
        assert pac.compute_pac(np.array([]), np.array([])) == 0.0

    def test_history_logged(self):
        pac = PhaseAmplitudeCoupling()
        pac.compute_pac(np.random.randn(50), np.random.randn(50))
        assert len(pac._coupling_history) == 1


class TestTemporalBinding:
    def test_bind_features_within_tolerance(self):
        tb = TemporalBinding(tolerance_ms=20.0)
        features = ["f1", "f2", "f3", "f4"]
        timestamps = np.array([0.0, 0.01, 0.015, 0.05])
        bindings = tb.bind(features, timestamps)
        assert len(bindings) >= 1
        assert any(len(b) >= 2 for b in bindings)

    def test_bind_no_features(self):
        tb = TemporalBinding()
        assert tb.bind([], np.array([])) == []

    def test_bind_all_separate(self):
        tb = TemporalBinding(tolerance_ms=1.0)
        features = ["f1", "f2"]
        timestamps = np.array([0.0, 0.1])
        bindings = tb.bind(features, timestamps)
        assert all(len(b) == 1 for b in bindings)


class TestNeuralOscillationsSystem:
    def test_step_produces_signal(self):
        sys = NeuralOscillationsSystem(n_channels=4)
        signal = sys.step(dt=0.001)
        assert signal.shape == (4,)

    def test_get_band_powers(self):
        sys = NeuralOscillationsSystem(n_channels=4)
        signal = np.random.randn(100)
        powers = sys.get_band_powers(signal)
        assert "theta" in powers
        assert "gamma" in powers
        assert all(v >= 0.0 for v in powers.values())

    def test_empty_signal(self):
        sys = NeuralOscillationsSystem(n_channels=4)
        powers = sys.get_band_powers(np.array([]))
        assert all(v == 0.0 for v in powers.values())

    def test_compute_coupling(self):
        sys = NeuralOscillationsSystem(n_channels=8)
        for _ in range(200):
            sys.step(dt=0.001)
        coupling = sys.compute_coupling(phase_idx=0, amp_idx=4)
        assert coupling >= 0.0

    def test_get_system_state(self):
        sys = NeuralOscillationsSystem(n_channels=4)
        state = sys.get_system_state()
        assert "time" in state
        assert "oscillator_bands" in state
