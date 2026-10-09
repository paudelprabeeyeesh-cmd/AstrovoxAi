import math

import pytest

from self_supervised_learning.contrastive_loss import (
    InfoNCEConfig,
    NTXentConfig,
    cosine_similarity,
    cosine_similarity_matrix,
    info_nce_loss,
    nt_xent_loss,
)


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 2.0, 3.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_zero_vector(self):
        v = [0.0, 0.0]
        result = cosine_similarity(v, [1.0, 2.0])
        assert math.isfinite(result)

    def test_symmetric(self):
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0]
        assert cosine_similarity(a, b) == pytest.approx(cosine_similarity(b, a))


class TestCosineSimilarityMatrix:
    def test_square_matrix(self):
        vectors = [[1.0, 0.0], [0.0, 1.0]]
        matrix = cosine_similarity_matrix(vectors)
        assert len(matrix) == 2
        assert all(len(row) == 2 for row in matrix)

    def test_diagonal_is_one(self):
        vectors = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
        matrix = cosine_similarity_matrix(vectors)
        for i in range(len(vectors)):
            assert matrix[i][i] == pytest.approx(1.0)

    def test_symmetric(self):
        vectors = [[1.0, 2.0], [3.0, 4.0]]
        matrix = cosine_similarity_matrix(vectors)
        assert matrix[0][1] == pytest.approx(matrix[1][0])


class TestNTXentLoss:
    def test_positive_pair_lower_than_negative(self):
        z_i = [[1.0, 0.0], [0.0, 1.0]]
        z_j = [[1.0, 0.0], [0.0, 1.0]]
        loss = nt_xent_loss(z_i, z_j, temperature=0.1)
        assert loss >= 0.0

    def test_returns_scalar(self):
        z_i = [[1.0, 0.0]]
        z_j = [[1.0, 0.0]]
        loss = nt_xent_loss(z_i, z_j, temperature=0.1)
        assert isinstance(loss, float)

    def test_batch_size_mismatch_raises(self):
        z_i = [[1.0, 0.0]]
        z_j = [[1.0, 0.0], [0.0, 1.0]]
        with pytest.raises(AssertionError):
            nt_xent_loss(z_i, z_j, temperature=0.1)

    def test_config_dataclass(self):
        config = NTXentConfig(temperature=0.5)
        assert config.temperature == pytest.approx(0.5)


class TestInfoNCELoss:
    def test_returns_scalar(self):
        query = [1.0, 0.0]
        positive = [1.0, 0.0]
        negatives = [[0.0, 1.0]]
        loss = info_nce_loss(query, positive, negatives, temperature=0.1)
        assert isinstance(loss, float)

    def test_positive_higher_than_negative_gives_low_loss(self):
        query = [1.0, 0.0]
        positive = [1.0, 0.0]
        negatives = [[0.0, 1.0]]
        loss = info_nce_loss(query, positive, negatives, temperature=0.1)
        assert loss >= 0.0

    def test_config_dataclass(self):
        config = InfoNCEConfig(temperature=0.5)
        assert config.temperature == pytest.approx(0.5)
