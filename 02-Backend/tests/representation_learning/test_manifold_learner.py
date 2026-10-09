import numpy as np
from representation_learning.manifold_learner import ManifoldLearner, ManifoldConfig


class TestManifoldLearner:
    def test_initialization(self):
        config = ManifoldConfig(input_dim=4, n_components=2)
        model = ManifoldLearner(config)
        assert model.config.input_dim == 4
        assert model.config.n_components == 2
        assert model.embedding is None

    def test_fit_sets_embedding(self):
        config = ManifoldConfig(input_dim=4, n_components=2, n_neighbors=3)
        model = ManifoldLearner(config)
        x = np.random.randn(20, 4).astype(np.float64)
        model.fit(x)
        assert model.embedding is not None
        assert model.embedding.shape == (20, 2)

    def test_fit_transform_shape(self):
        config = ManifoldConfig(input_dim=4, n_components=2, n_neighbors=3)
        model = ManifoldLearner(config)
        x = np.random.randn(20, 4).astype(np.float64)
        embedding = model.fit_transform(x)
        assert embedding.shape == (20, 2)

    def test_transform_after_fit(self):
        config = ManifoldConfig(input_dim=4, n_components=2, n_neighbors=3)
        model = ManifoldLearner(config)
        x = np.random.randn(20, 4).astype(np.float64)
        model.fit(x)
        emb = model.transform(x)
        assert emb.shape == (20, 2)

    def test_transform_before_fit_raises(self):
        config = ManifoldConfig(input_dim=4)
        model = ManifoldLearner(config)
        x = np.random.randn(10, 4).astype(np.float64)
        with np.testing.assert_raises(RuntimeError):
            model.transform(x)

    def test_reconstruction_error(self):
        config = ManifoldConfig(input_dim=4, n_components=2, n_neighbors=3)
        model = ManifoldLearner(config)
        x = np.random.randn(20, 4).astype(np.float64)
        model.fit(x)
        err = model.reconstruction_error(x)
        assert isinstance(err, float)
        assert err >= 0.0

    def test_get_report(self):
        config = ManifoldConfig(input_dim=4, n_components=2, n_neighbors=3)
        model = ManifoldLearner(config)
        x = np.random.randn(20, 4).astype(np.float64)
        model.fit(x)
        report = model.get_report()
        assert report["fitted"] is True
        assert report["n_components"] == 2
        assert report["n_neighbors"] == 3
        assert report["embedding_shape"] == [20, 2]

    def test_spectral_embedding_deterministic(self):
        np.random.seed(42)
        config = ManifoldConfig(input_dim=4, n_components=2, n_neighbors=3)
        x = np.random.randn(20, 4).astype(np.float64)
        model = ManifoldLearner(config)
        emb1 = model.fit_transform(x)

        np.random.seed(42)
        config2 = ManifoldConfig(input_dim=4, n_components=2, n_neighbors=3)
        model2 = ManifoldLearner(config2)
        emb2 = model2.fit_transform(x)
        np.testing.assert_allclose(emb1, emb2, atol=1e-6)
