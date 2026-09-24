import numpy as np
from typing import List, Dict, Any
from dataclasses import dataclass
import time


@dataclass
class OscillationState:
    frequency: float
    amplitude: float
    phase: float
    band: str
    power: float = 1.0


class NeuralOscillator:
    def __init__(self, frequency: float = 10.0, amplitude: float = 1.0, phase: float = 0.0):
        self.frequency = frequency
        self.amplitude = amplitude
        self.phase = phase
        self.band = self._classify_band(frequency)

    def _classify_band(self, freq: float) -> str:
        if freq < 4:
            return "delta"
        if freq < 8:
            return "theta"
        if freq < 13:
            return "alpha"
        if freq < 30:
            return "beta"
        if freq < 100:
            return "gamma"
        return "high_gamma"

    def sample(self, t: float) -> float:
        return self.amplitude * np.sin(2 * np.pi * self.frequency * t + self.phase)

    def update(self, dt: float, coupling: float = 0.0) -> None:
        self.phase += 2 * np.pi * self.frequency * dt
        self.phase %= 2 * np.pi
        self.amplitude = max(0.1, self.amplitude + coupling * dt)
        self.phase += coupling * dt * 0.1


class PhaseAmplitudeCoupling:
    def __init__(self, phase_band: str = "theta", amplitude_band: str = "gamma"):
        self.phase_band = phase_band
        self.amplitude_band = amplitude_band
        self._coupling_history: List[Dict[str, Any]] = []

    def compute_pac(self, phase_signal: np.ndarray, amplitude_signal: np.ndarray,
                    n_bins: int = 18) -> float:
        if len(phase_signal) == 0 or len(amplitude_signal) == 0:
            return 0.0
        phase = np.angle(np.exp(1j * phase_signal))
        amplitude = np.abs(amplitude_signal)
        bins = np.linspace(-np.pi, np.pi, n_bins + 1)
        pac_values = []
        for i in range(n_bins):
            mask = (phase >= bins[i]) & (phase < bins[i + 1])
            if np.any(mask):
                pac_values.append(float(np.mean(amplitude[mask])))
            else:
                pac_values.append(0.0)
        pac = np.std(pac_values) if pac_values else 0.0
        self._coupling_history.append({
            "pac": float(pac),
            "timestamp": time.time(),
        })
        return float(pac)


class TemporalBinding:
    def __init__(self, tolerance_ms: float = 20.0):
        self.tolerance_ms = tolerance_ms
        self._bindings: List[Dict[str, Any]] = []

    def bind(self, features: List[Any], timestamps: np.ndarray) -> List[List[Any]]:
        if len(features) == 0:
            return []
        sorted_indices = np.argsort(timestamps)
        sorted_features = [features[i] for i in sorted_indices]
        sorted_ts = timestamps[sorted_indices]
        bindings = []
        current_binding = [sorted_features[0]]
        current_time = sorted_ts[0]
        for i in range(1, len(sorted_features)):
            if abs(sorted_ts[i] - current_time) <= self.tolerance_ms / 1000.0:
                current_binding.append(sorted_features[i])
            else:
                if len(current_binding) > 1:
                    bindings.append(current_binding)
                current_binding = [sorted_features[i]]
            current_time = sorted_ts[i]
        if len(current_binding) > 1:
            bindings.append(current_binding)
        self._bindings.append({
            "bindings_count": len(bindings),
            "timestamp": time.time(),
        })
        return bindings


class NeuralOscillationsSystem:
    def __init__(self, n_channels: int = 8):
        self.n_channels = n_channels
        self.oscillators: List[NeuralOscillator] = []
        for _ in range(n_channels):
            freq = np.random.choice([2.0, 6.0, 10.0, 20.0, 40.0, 80.0])
            amp = 0.5 + np.random.random() * 0.5
            self.oscillators.append(NeuralOscillator(frequency=freq, amplitude=amp))
        self.pac = PhaseAmplitudeCoupling()
        self.temporal_binding = TemporalBinding()
        self._time = 0.0
        self._history: List[np.ndarray] = []

    def step(self, dt: float = 0.001) -> np.ndarray:
        signals = []
        for osc in self.oscillators:
            osc.update(dt)
            signals.append(osc.sample(self._time))
        self._time += dt
        signal_array = np.array(signals)
        self._history.append(signal_array)
        if len(self._history) > 1000:
            self._history = self._history[-1000:]
        return signal_array

    def get_band_powers(self, signal_window: np.ndarray) -> Dict[str, float]:
        if signal_window.size == 0:
            return {"delta": 0.0, "theta": 0.0, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}
        fft = np.fft.rfft(signal_window)
        power = np.abs(fft) ** 2
        freqs = np.fft.rfftfreq(len(signal_window), d=0.001)
        band_powers = {}
        for band, (low, high) in [("delta", (0.5, 4)), ("theta", (4, 8)), ("alpha", (8, 13)),
                                   ("beta", (13, 30)), ("gamma", (30, 100))]:
            mask = (freqs >= low) & (freqs < high)
            band_powers[band] = float(np.sum(power[mask])) if np.any(mask) else 0.0
        return band_powers

    def compute_coupling(self, phase_idx: int = 0, amp_idx: int = 4) -> float:
        if len(self._history) < 2:
            return 0.0
        window = np.array(self._history[-100:])
        if window.shape[1] <= max(phase_idx, amp_idx):
            return 0.0
        phase_signal = window[:, phase_idx]
        amp_signal = window[:, amp_idx]
        return self.pac.compute_pac(phase_signal, amp_signal)

    def get_system_state(self) -> Dict[str, Any]:
        return {
            "time": self._time,
            "oscillator_bands": [osc.band for osc in self.oscillators],
            "history_length": len(self._history),
        }
