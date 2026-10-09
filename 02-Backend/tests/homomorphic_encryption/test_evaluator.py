import pytest

from homomorphic_encryption.ciphertext import CiphertextOps, Ciphertext
from homomorphic_encryption.evaluator import Evaluator, EvaluationResult
from homomorphic_encryption.key_manager import KeyManager


class TestEvaluatorAddition:
    def test_add_two_ciphertexts(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        ops = CiphertextOps(pub, priv)
        eval_ = Evaluator(pub, priv)
        ct1 = ops.encrypt(3)
        ct2 = ops.encrypt(4)
        result = eval_.evaluate_add(ct1, ct2)
        assert eval_.decrypt_result(result) == 7

    def test_add_commutative(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        ops = CiphertextOps(pub, priv)
        eval_ = Evaluator(pub, priv)
        ct1 = ops.encrypt(10)
        ct2 = ops.encrypt(20)
        res1 = eval_.evaluate_add(ct1, ct2)
        res2 = eval_.evaluate_add(ct2, ct1)
        assert eval_.decrypt_result(res1) == eval_.decrypt_result(res2)

    def test_add_identity(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        ops = CiphertextOps(pub, priv)
        eval_ = Evaluator(pub, priv)
        ct1 = ops.encrypt(15)
        ct_zero = ops.encrypt(0)
        result = eval_.evaluate_add(ct1, ct_zero)
        assert eval_.decrypt_result(result) == 15

    def test_add_mismatched_keys_raises(self):
        km1 = KeyManager(key_size=128, seed=1)
        km2 = KeyManager(key_size=128, seed=2)
        pub1, priv1 = km1.generate_keys()
        pub2, _ = km2.generate_keys()
        ops1 = CiphertextOps(pub1, priv1)
        ops2 = CiphertextOps(pub2)
        ct1 = ops1.encrypt(1)
        ct2 = ops2.encrypt(2)
        eval_ = Evaluator(pub1, priv1)
        with pytest.raises(ValueError):
            eval_.evaluate_add(ct1, ct2)


class TestEvaluatorMultiplication:
    def test_multiply_by_scalar(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        ops = CiphertextOps(pub, priv)
        eval_ = Evaluator(pub, priv)
        ct = ops.encrypt(6)
        result = eval_.evaluate_mul(ct, 3)
        assert eval_.decrypt_result(result) == 18

    def test_multiply_by_zero(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        ops = CiphertextOps(pub, priv)
        eval_ = Evaluator(pub, priv)
        ct = ops.encrypt(99)
        result = eval_.evaluate_mul(ct, 0)
        assert eval_.decrypt_result(result) == 0

    def test_multiply_by_one(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        ops = CiphertextOps(pub, priv)
        eval_ = Evaluator(pub, priv)
        ct = ops.encrypt(7)
        result = eval_.evaluate_mul(ct, 1)
        assert eval_.decrypt_result(result) == 7


class TestEvaluatorSum:
    def test_sum_multiple_ciphertexts(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        ops = CiphertextOps(pub, priv)
        eval_ = Evaluator(pub, priv)
        values = [1, 2, 3, 4, 5]
        cts = [ops.encrypt(v) for v in values]
        result = eval_.evaluate_sum(cts)
        assert eval_.decrypt_result(result) == sum(values)

    def test_sum_empty_raises(self):
        km = KeyManager(key_size=128)
        pub, _ = km.generate_keys()
        eval_ = Evaluator(pub)
        with pytest.raises(ValueError):
            eval_.evaluate_sum([])


class TestEvaluatorDecrypt:
    def test_decrypt_without_private_key_raises(self):
        km = KeyManager(key_size=128)
        pub, _ = km.generate_keys()
        ops = CiphertextOps(pub)
        ct = ops.encrypt(1)
        eval_ = Evaluator(pub)
        result = EvaluationResult(ciphertext=ct, noise_level=0.1)
        with pytest.raises(ValueError):
            eval_.decrypt_result(result)
