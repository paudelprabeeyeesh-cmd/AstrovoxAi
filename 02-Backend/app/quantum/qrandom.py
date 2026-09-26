import numpy as np
from typing import List, Optional
from dataclasses import dataclass
from .circuit_simulator import QuantumCircuitSimulator

@dataclass
class QuantumRandomResult:
    random_bytes: bytes
    entropy: float
    source: str

class QuantumRandomNumberGenerator:
    def __init__(self, num_qubits: int = 8, seed: Optional[int] = None):
        self.num_qubits = num_qubits
        if seed is not None:
            np.random.seed(seed)

    def generate(self, shots: int = 1) -> QuantumRandomResult:
        sim = QuantumCircuitSimulator(self.num_qubits)
        for i in range(self.num_qubits):
            sim.h(i)
        result = sim.run(shots=shots)
        all_bits = []
        for count in result.counts.values():
            bits = int(list(result.counts.keys())[list(result.counts.values()).index(count)])
            all_bits.extend([int(b) for b in format(bits, f"0{self.num_qubits}b")])
        random_bytes = bytes(int("".join(map(str, all_bits[i:i + 8])), 2) % 256 for i in range(0, len(all_bits) - 7, 8))
        probs = list(result.probabilities.values())
        entropy = float(-sum(p * np.log2(p + 1e-10) for p in probs))
        return QuantumRandomResult(random_bytes=random_bytes, entropy=entropy, source="quantum_hadamard")

    def generate_int(self, min_val: int, max_val: int) -> int:
        result = self.generate()
        val = int.from_bytes(result.random_bytes, "big")
        return min_val + (val % (max_val - min_val + 1))

    def generate_float(self) -> float:
        result = self.generate()
        val = int.from_bytes(result.random_bytes, "big")
        return val / (2 ** (len(result.random_bytes) * 8))

    def generate_uniform(self, size: int) -> np.ndarray:
        results = []
        for _ in range(size):
            result = self.generate()
            val = int.from_bytes(result.random_bytes, "big")
            results.append(val / (2 ** (len(result.random_bytes) * 8)))
        return np.array(results)

    def generate_normal(self, size: int, mean: float = 0.0, std: float = 1.0) -> np.ndarray:
        uniforms = self.generate_uniform(size * 2)
        u1 = uniforms[:size]
        u2 = uniforms[size:]
        z0 = np.sqrt(-2.0 * np.log(u1 + 1e-10)) * np.cos(2.0 * np.pi * u2)
        return z0 * std + mean

    def generate_coin_flip(self, num_flips: int) -> List[int]:
        result = self.generate()
        bits = []
        for byte in result.random_bytes:
            for i in range(8):
                if len(bits) >= num_flips:
                    break
                bits.append((byte >> i) & 1)
        return bits[:num_flips]

    def generate_shuffle(self, items: List[int]) -> List[int]:
        items = items.copy()
        n = len(items)
        for i in range(n - 1, 0, -1):
            j = self.generate_int(0, i)
            items[i], items[j] = items[j], items[i]
        return items

    def quantum_seed(self) -> int:
        result = self.generate()
        return int.from_bytes(result.random_bytes[:8], "big")

    def generate_password(self, length: int = 16, charset: str = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*") -> str:
        result = self.generate()
        bytes_needed = length * 2
        password = []
        idx = 0
        for _ in range(length):
            if idx + 2 > len(result.random_bytes):
                result = self.generate()
                idx = 0
            val = int.from_bytes(result.random_bytes[idx:idx + 2], "big")
            password.append(charset[val % len(charset)])
            idx += 2
        return "".join(password)
