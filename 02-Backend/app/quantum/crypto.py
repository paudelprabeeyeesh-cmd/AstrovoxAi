import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import hashlib
import secrets
import struct
from .circuit_simulator import QuantumCircuitSimulator
@dataclass
class QKDKeyPair:
    alice_key: str
    bob_key: str
    error_rate: float
    sifted_key_length: int

class QuantumCrypto:
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            np.random.seed(seed)

    def bb84(self, num_bits: int = 256) -> QKDKeyPair:
        alice_bits = np.random.randint(0, 2, num_bits)
        alice_bases = np.random.randint(0, 2, num_bits)
        bob_bases = np.random.randint(0, 2, num_bits)
        bob_results = []
        for i in range(num_bits):
            sim = QuantumCircuitSimulator(1)
            if alice_bits[i] == 1:
                sim.x(0)
            if alice_bases[i] == 1:
                sim.h(0)
            if bob_bases[i] == 1:
                sim.h(0)
            result = sim.run(shots=1)
            measured = int(list(result.counts.keys())[0])
            if bob_bases[i] == 1:
                sim2 = QuantumCircuitSimulator(1)
                sim2.x(0) if measured else None
                sim2.h(0)
                result2 = sim2.run(shots=1)
                measured = int(list(result2.counts.keys())[0])
            bob_results.append(measured)
        alice_key = "".join(str(b) for i, b in enumerate(alice_bits) if alice_bases[i] == bob_bases[i])
        bob_key = "".join(str(b) for i, b in enumerate(bob_results) if alice_bases[i] == bob_bases[i])
        min_len = min(len(alice_key), len(bob_key))
        alice_key = alice_key[:min_len]
        bob_key = bob_key[:min_len]
        errors = sum(a != b for a, b in zip(alice_key, bob_key))
        error_rate = errors / max(min_len, 1)
        return QKDKeyPair(alice_key=alice_key, bob_key=bob_key, error_rate=error_rate, sifted_key_length=min_len)

    def e91_protocol(self, num_pairs: int = 128) -> Tuple[str, str]:
        alice_bits = []
        bob_bits = []
        for _ in range(num_pairs):
            sim = QuantumCircuitSimulator(2)
            sim.h(0)
            sim.cnot(0, 1)
            bases_a = np.random.choice(["X", "Z"])
            bases_b = np.random.choice(["X", "Z"])
            if bases_a == "X":
                sim.h(0)
            if bases_b == "X":
                sim.h(1)
            result = sim.run(shots=1)
            bits = list(result.counts.keys())[0]
            alice_bits.append(bits[0])
            bob_bits.append(bits[1])
        key = "".join(a for a, b in zip(alice_bits, bob_bits) if np.random.rand() > 0.5)
        return key, key

    def quantum_otp(self, message: bytes, key: Optional[str] = None) -> Tuple[bytes, str]:
        if key is None:
            key = "".join(str(np.random.randint(0, 2)) for _ in range(len(message) * 8))
        key_bytes = int(key[:len(message) * 8], 2).to_bytes(len(message), "big")
        encrypted = bytes(m ^ k for m, k in zip(message, key_bytes))
        return encrypted, key

    def decrypt_otp(self, ciphertext: bytes, key: str) -> bytes:
        key_bytes = int(key[:len(ciphertext) * 8], 2).to_bytes(len(ciphertext), "big")
        return bytes(c ^ k for c, k in zip(ciphertext, key_bytes))

    def quantum_hash(self, data: bytes) -> str:
        sim = QuantumCircuitSimulator(8)
        for i, byte in enumerate(data[:8]):
            for j in range(8):
                if (byte >> j) & 1:
                    sim.x(i)
            sim.h(i)
        result = sim.run(shots=1)
        hash_val = list(result.counts.keys())[0]
        return hashlib.sha256((hash_val + data.decode("latin-1", errors="ignore")).encode()).hexdigest()

    def quantum_signature(self, message: bytes, private_key: str) -> str:
        sim = QuantumCircuitSimulator(4)
        for i, bit in enumerate(private_key[:4]):
            if bit == "1":
                sim.x(i)
            sim.h(i)
        msg_hash = hashlib.sha256(message).digest()[:4]
        for i, byte in enumerate(msg_hash):
            if byte & 1:
                sim.cnot(i, (i + 1) % 4)
        result = sim.run(shots=1)
        return list(result.counts.keys())[0] + private_key[4:]

    def verify_signature(self, message: bytes, signature: str, public_key: str) -> bool:
        expected = self.quantum_signature(message, public_key)
        return signature[:4] == expected[:4]

    def quantum_secure_hash(self, data: str) -> str:
        sim = QuantumCircuitSimulator(10)
        encoded = data.encode("utf-8")
        for i in range(min(10, len(encoded))):
            for j in range(8):
                if (encoded[i] >> j) & 1:
                    bit_idx = i * 8 + j
                    if bit_idx < sim.num_qubits:
                        sim.x(bit_idx % sim.num_qubits)
        for i in range(sim.num_qubits):
            sim.h(i)
            if i < sim.num_qubits - 1:
                sim.cnot(i, i + 1)
        result = sim.run(shots=1)
        return list(result.counts.keys())[0]
