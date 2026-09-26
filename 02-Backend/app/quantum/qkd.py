import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass
from .crypto import QuantumCrypto
from .circuit_simulator import QuantumCircuitSimulator

@dataclass
class QKDProtocolResult:
    raw_key: str
    sifted_key: str
    error_rate: float
    key_rate: float
    protocol: str

class QuantumKeyDistribution:
    def __init__(self, seed: Optional[int] = None):
        self.crypto = QuantumCrypto(seed=seed)
        if seed is not None:
            np.random.seed(seed)

    def bb84(self, num_bits: int = 256, error_threshold: float = 0.11) -> QKDProtocolResult:
        result = self.crypto.bb84(num_bits)
        if result.error_rate > error_threshold:
            return QKDProtocolResult(
                raw_key="",
                sifted_key="",
                error_rate=result.error_rate,
                key_rate=0.0,
                protocol="BB84",
            )
        key_rate = len(result.bob_key) / num_bits
        return QKDProtocolResult(
            raw_key=result.alice_key,
            sifted_key=result.bob_key,
            error_rate=result.error_rate,
            key_rate=key_rate,
            protocol="BB84",
        )

    def e91(self, num_pairs: int = 128) -> QKDProtocolResult:
        key1, key2 = self.crypto.e91_protocol(num_pairs)
        error_rate = sum(a != b for a, b in zip(key1, key2)) / max(len(key1), 1)
        return QKDProtocolResult(
            raw_key=key1,
            sifted_key=key2,
            error_rate=error_rate,
            key_rate=len(key2) / num_pairs,
            protocol="E91",
        )

    def b92(self, num_bits: int = 256) -> QKDProtocolResult:
        alice_bits = np.random.randint(0, 2, num_bits)
        alice_bases = np.random.choice([0, 1], size=num_bits, p=[0.5, 0.5])
        bob_bases = np.random.choice([0, 1], size=num_bits, p=[0.5, 0.5])
        bob_results = []
        for i in range(num_bits):
            sim = QuantumCircuitSimulator(1)
            if alice_bits[i] == 1:
                sim.x(0)
            if alice_bases[i] == 1:
                sim.h(0)
            if bob_bases[i] == 0:
                sim.h(0)
            result = sim.run(shots=1)
            measured = int(list(result.counts.keys())[0])
            bob_results.append(measured)
        matching = [i for i in range(num_bits) if alice_bases[i] != bob_bases[i]]
        raw_key = "".join(str(alice_bits[i]) for i in matching)
        sifted = "".join(str(bob_results[i]) for i in matching)
        error_rate = sum(a != b for a, b in zip(raw_key, sifted)) / max(len(raw_key), 1)
        return QKDProtocolResult(
            raw_key=raw_key,
            sifted_key=sifted,
            error_rate=error_rate,
            key_rate=len(sifted) / num_bits,
            protocol="B92",
        )

    def privacy_amplification(self, key: str, security_parameter: int = 128) -> str:
        sim = QuantumCircuitSimulator(min(len(key), 16))
        for i, bit in enumerate(key[:sim.num_qubits]):
            if bit == "1":
                sim.x(i)
            sim.h(i)
        for i in range(sim.num_qubits - 1):
            sim.cnot(i, i + 1)
        result = sim.run(shots=1)
        amplified = list(result.counts.keys())[0]
        return amplified[:security_parameter]

    def error_correction(self, key1: str, key2: str) -> Tuple[str, str]:
        min_len = min(len(key1), len(key2))
        k1 = key1[:min_len]
        k2 = key2[:min_len]
        errors = [i for i in range(min_len) if k1[i] != k2[i]]
        corrected = list(k2)
        parity = sum(int(b) for b in k2) % 2
        for i in errors:
            corrected[i] = str(1 - int(corrected[i]))
        return k1, "".join(corrected)

    def generate_shared_secret(self, key_length: int = 256) -> Tuple[str, str]:
        result = self.bb84(key_length)
        if result.error_rate < 0.11 and len(result.sifted_key) >= 128:
            secret = self.privacy_amplification(result.sifted_key)
            return secret, result.sifted_key
        return "", result.sifted_key
