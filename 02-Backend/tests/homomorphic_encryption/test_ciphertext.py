import pytest

from homomorphic_encryption.ciphertext import CiphertextOps, Ciphertext
from homomorphic_encryption.key_manager import KeyManager


class TestCiphertextRoundtrip:
    def test_encrypt_decrypt_zero(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        ops = CiphertextOps(pub, priv)
        ct = ops.encrypt(0)
        assert ops.decrypt(ct) == 0

    def test_encrypt_decrypt_small(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        ops = CiphertextOps(pub, priv)
        ct = ops.encrypt(42)
        assert ops.decrypt(ct) == 42

    def test_encrypt_decrypt_large(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        ops = CiphertextOps(pub, priv)
        value = pub.n - 1
        ct = ops.encrypt(value)
        assert ops.decrypt(ct) == value

    def test_encrypt_without_private_key_does_not_decrypt(self):
        km = KeyManager(key_size=128)
        pub, _ = km.generate_keys()
        ops = CiphertextOps(pub)
        ct = ops.encrypt(7)
        with pytest.raises(ValueError):
            ops.decrypt(ct)

    def test_different_randomness_different_ciphertexts(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        ops = CiphertextOps(pub, priv)
        ct1 = ops.encrypt(5)
        ct2 = ops.encrypt(5)
        assert ct1.value != ct2.value

    def test_decrypt_after_multiple_encryptions(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        ops = CiphertextOps(pub, priv)
        for val in [0, 1, 10, 100, 1000]:
            ct = ops.encrypt(val)
            assert ops.decrypt(ct) == val


class TestCiphertextOps:
    def test_add_two_ciphertexts(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        ops = CiphertextOps(pub, priv)
        ct1 = ops.encrypt(3)
        ct2 = ops.encrypt(4)
        result = ops.add(ct1, ct2)
        assert ops.decrypt(result) == 7

    def test_add_mismatched_keys_raises(self):
        km1 = KeyManager(key_size=128, seed=1)
        km2 = KeyManager(key_size=128, seed=2)
        pub1, priv1 = km1.generate_keys()
        pub2, _ = km2.generate_keys()
        ops1 = CiphertextOps(pub1, priv1)
        ops2 = CiphertextOps(pub2)
        ct1 = ops1.encrypt(1)
        ct2 = ops2.encrypt(2)
        with pytest.raises(ValueError):
            ops1.add(ct1, ct2)

    def test_multiply_by_scalar(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        ops = CiphertextOps(pub, priv)
        ct = ops.encrypt(6)
        result = ops.multiply(ct, 3)
        assert ops.decrypt(result) == 18

    def test_multiply_by_zero(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        ops = CiphertextOps(pub, priv)
        ct = ops.encrypt(99)
        result = ops.multiply(ct, 0)
        assert ops.decrypt(result) == 0

    def test_encrypt_returns_ciphertext_with_public_key(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        ops = CiphertextOps(pub, priv)
        ct = ops.encrypt(5)
        assert ct.public_key.n == pub.n
