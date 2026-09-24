import pytest

from homomorphic_encryption.key_manager import KeyManager, PublicKey, PrivateKey


class TestKeyGeneration:
    def test_generate_keys_returns_pair(self):
        km = KeyManager(key_size=128)
        pub, priv = km.generate_keys()
        assert isinstance(pub, PublicKey)
        assert isinstance(priv, PrivateKey)

    def test_public_key_attributes(self):
        km = KeyManager(key_size=128)
        pub, _ = km.generate_keys()
        assert pub.n > 0
        assert pub.g == pub.n + 1

    def test_private_key_attributes(self):
        km = KeyManager(key_size=128)
        _, priv = km.generate_keys()
        assert priv.n > 0
        assert priv.lambda_ > 0
        assert priv.mu > 0

    def test_deterministic_with_seed(self):
        km1 = KeyManager(key_size=128, seed=42)
        km2 = KeyManager(key_size=128, seed=42)
        pub1, priv1 = km1.generate_keys()
        pub2, priv2 = km2.generate_keys()
        assert pub1.n == pub2.n
        assert pub1.g == pub2.g

    def test_different_seeds_produce_different_keys(self):
        km1 = KeyManager(key_size=128, seed=1)
        km2 = KeyManager(key_size=128, seed=2)
        pub1, _ = km1.generate_keys()
        pub2, _ = km2.generate_keys()
        assert pub1.n != pub2.n


class TestKeyExportImport:
    def test_export_keys(self):
        km = KeyManager(key_size=128)
        km.generate_keys()
        pub, priv = km.export_keys()
        assert len(pub) == 2
        assert len(priv) == 3

    def test_import_keys(self):
        km = KeyManager(key_size=128)
        km.generate_keys()
        pub, priv = km.export_keys()
        km2 = KeyManager(key_size=128)
        km2.import_keys(pub, priv)
        assert km2.public_key.n == km.public_key.n
        assert km2.private_key.mu == km.private_key.mu

    def test_import_keys_before_generate_raises(self):
        km = KeyManager(key_size=128)
        with pytest.raises(ValueError):
            km.export_keys()
