import pytest

from homomorphic_encryption.ciphertext import CiphertextOps
from homomorphic_encryption.evaluator import Evaluator, EvaluationResult
from homomorphic_encryption.key_manager import KeyManager
from homomorphic_encryption.noise_reducer import NoiseReducer, NoiseBudget


class TestNoiseBudget:
    def test_initial_budget(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        eval_ = Evaluator(pub, priv)
        reducer = NoiseReducer(eval_)
        assert reducer.noise_budget.current_noise == 0.0
        assert reducer.noise_budget.threshold == 0.8

    def test_remaining_budget(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        eval_ = Evaluator(pub, priv)
        reducer = NoiseReducer(eval_)
        assert reducer.remaining_budget() == 1.0


class TestNoiseTracking:
    def test_track_noise_updates_current(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        eval_ = Evaluator(pub, priv)
        ops = CiphertextOps(pub, priv)
        reducer = NoiseReducer(eval_)
        ct = ops.encrypt(5)
        result = EvaluationResult(ciphertext=ct, noise_level=0.5)
        reducer.track_noise(result)
        assert reducer.noise_budget.current_noise == 0.5

    def test_track_noise_keeps_max(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        eval_ = Evaluator(pub, priv)
        ops = CiphertextOps(pub, priv)
        reducer = NoiseReducer(eval_)
        ct = ops.encrypt(5)
        reducer.track_noise(EvaluationResult(ciphertext=ct, noise_level=0.3))
        reducer.track_noise(EvaluationResult(ciphertext=ct, noise_level=0.9))
        assert reducer.noise_budget.current_noise == 0.9


class TestNoiseReduction:
    def test_reduce_when_below_threshold(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        ops = CiphertextOps(pub, priv)
        eval_ = Evaluator(pub, priv)
        reducer = NoiseReducer(eval_)
        ct = ops.encrypt(11)
        result = EvaluationResult(ciphertext=ct, noise_level=0.1)
        reduced = reducer.reduce(result)
        assert reduced.noise_level < result.noise_level or reduced.noise_level == result.noise_level
        assert eval_.decrypt_result(reduced) == 11

    def test_reduce_when_above_threshold(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        ops = CiphertextOps(pub, priv)
        eval_ = Evaluator(pub, priv)
        reducer = NoiseReducer(eval_)
        ct = ops.encrypt(22)
        result = EvaluationResult(ciphertext=ct, noise_level=0.95)
        reduced = reducer.reduce(result)
        assert eval_.decrypt_result(reduced) == 22
        assert reduced.noise_level < result.noise_level

    def test_reduce_without_private_key_raises(self):
        km = KeyManager(key_size=128)
        pub, _ = km.generate_keys()
        ops = CiphertextOps(pub)
        eval_ = Evaluator(pub)
        ct = ops.encrypt(1)
        result = EvaluationResult(ciphertext=ct, noise_level=0.95)
        reducer = NoiseReducer(eval_)
        with pytest.raises(ValueError):
            reducer.reduce(result)
