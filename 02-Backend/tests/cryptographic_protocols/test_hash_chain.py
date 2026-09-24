import hashlib
import pytest
from cryptographic_protocols.hash_chain import (
    HashChain,
    IteratedHashFunction,
    OneWayAccumulator,
)


def test_hash_chain_defaults():
    chain = HashChain()
    assert len(chain._chain) == 1000
    assert chain.root == hashlib.sha256(b"seed").digest()


def test_hash_chain_values():
    chain = HashChain(seed=b"seed", length=5)
    values = [chain._chain[0], chain._chain[1], chain._chain[2], chain._chain[3], chain._chain[4]]
    assert chain.verify_chain(0, 4, values)


def test_hash_chain_single_value():
    chain = HashChain(seed=b"seed", length=5)
    assert chain.verify_chain(4, 4, [chain._chain[4]])


def test_hash_chain_next_value():
    chain = HashChain(seed=b"seed", length=5)
    current = chain.current_value()
    next_val = chain.next_value()
    assert next_val == chain._chain[3]
    expected = hashlib.sha256(current).digest()
    assert next_val == expected


def test_hash_chain_verify_fails_on_tamper():
    chain = HashChain(seed=b"seed", length=5)
    values = list(chain._chain[:5])
    values[2] = b"tampered"
    assert not chain.verify_chain(0, 4, values)


def test_hash_chain_root():
    chain = HashChain(seed=b"seed", length=10)
    assert chain.root == chain._chain[0]


def test_one_way_accumulator():
    values = [b"b", b"c", b"a"]
    acc = OneWayAccumulator.accumulate(values)
    witness = OneWayAccumulator.witness(b"a", values)
    assert OneWayAccumulator.verify(acc, b"a", witness)


def test_one_way_accumulator_empty():
    values = []
    acc = OneWayAccumulator.accumulate(values)
    witness = OneWayAccumulator.witness(b"missing", values)
    assert OneWayAccumulator.verify(acc, b"missing", witness)


def test_one_way_accumulator_invalid():
    values = [b"a", b"b"]
    acc = OneWayAccumulator.accumulate(values)
    wrong_witness = OneWayAccumulator.witness(b"a", values)
    assert not OneWayAccumulator.verify(acc, b"b", wrong_witness)


def test_iterated_hash_function():
    result = IteratedHashFunction.hash(b"message", iterations=100)
    assert len(result) == 32


def test_iterated_hash_function_default_iterations():
    result = IteratedHashFunction.hash(b"message")
    assert len(result) == 32


def test_iterated_hash_chain():
    chain = IteratedHashFunction.hash_chain(b"message", 5)
    assert len(chain) == 5
    assert chain[0] == b"message"
