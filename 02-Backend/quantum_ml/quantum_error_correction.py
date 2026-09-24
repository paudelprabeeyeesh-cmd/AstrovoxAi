import numpy as np
from typing import Tuple, Optional


class NoiseModel:
    def __init__(self, num_qubits: int):
        self.num_qubits = num_qubits
        self.p_depolarizing: float = 0.01
        self.p_amplitude_damping: float = 0.01
        self.p_phase_damping: float = 0.01
        self.p_readout: float = 0.01

    def depolarizing_channel(self, rho: np.ndarray, p: float) -> np.ndarray:
        dim = rho.shape[0]
        return (1 - p) * rho + p / dim * np.eye(dim)

    def amplitude_damping(self, rho: np.ndarray, gamma: float) -> np.ndarray:
        a = np.array([[1, 0], [0, np.sqrt(1 - gamma)]], dtype=np.complex128)
        b = np.array([[0, np.sqrt(gamma)], [0, 0]], dtype=np.complex128)
        kraus = [a, b]
        new_rho = np.zeros_like(rho, dtype=np.complex128)
        for k in kraus:
            new_rho += k @ rho @ np.conj(k).T
        return new_rho

    def phase_damping(self, rho: np.ndarray, lambda_: float) -> np.ndarray:
        e0 = np.array([[1, 0], [0, np.sqrt(1 - lambda_)]], dtype=np.complex128)
        e1 = np.array([[0, 0], [0, np.sqrt(lambda_)]], dtype=np.complex128)
        kraus = [e0, e1]
        new_rho = np.zeros_like(rho, dtype=np.complex128)
        for k in kraus:
            new_rho += k @ rho @ np.conj(k).T
        return new_rho

    def readout_error(self, prob: float) -> Tuple[np.ndarray, np.ndarray]:
        error_matrix = np.array([[1 - prob, prob], [prob, 1 - prob]], dtype=np.float64)
        return error_matrix, error_matrix.T

    def apply_noise_to_state(self, state: np.ndarray) -> np.ndarray:
        num_qubits = int(np.log2(len(state)))
        rho = np.outer(state, np.conj(state))
        for _ in range(self.num_qubits):
            rho = self.depolarizing_channel(rho, self.p_depolarizing)
        return rho


class ErrorMitigation:
    @staticmethod
    def zero_noise_extrapolation(fn, noises: List[float] = None, order: int = 2) -> float:
        if noises is None:
            noises = [0.0, 0.01, 0.02]
        values = [fn(noise) for noise in noises]
        if len(values) < 2:
            return values[0]
        coeffs = np.polyfit(noises, values, deg=min(order, len(noises) - 1))
        return float(np.polyval(coeffs, 0.0))

    @staticmethod
    def measurement_error_mitigation(counts: Dict[str, int], error_matrix: np.ndarray) -> Dict[str, float]:
        total = sum(counts.values())
        probs = {k: v / total for k, v in counts.items()}
        n = int(np.log2(len(error_matrix)))
        mitigated = {}
        for bitstring in probs:
            prob = probs[bitstring]
            idx = int(bitstring, 2)
            corrected = error_matrix[idx, idx] * prob
            for j in range(len(error_matrix)):
                if j != idx:
                    corrected += error_matrix[j, idx] * probs.get(format(j, f"0{n}b"), 0.0)
            mitigated[bitstring] = float(corrected)
        return mitigated

    @staticmethod
    def virtual_distillation(counts_list: List[Dict[str, int]]) -> Dict[str, float]:
        combined = {}
        for counts in counts_list:
            for bitstring, count in counts.items():
                combined[bitstring] = combined.get(bitstring, 0) + count / len(counts_list)
        total = sum(combined.values())
        return {k: v / total for k, v in combined.items()}

    @staticmethod
    def learning_dequantizing(fn, num_samples: int = 100) -> float:
        samples = []
        for _ in range(num_samples):
            samples.append(fn())
        return float(np.median(samples))
