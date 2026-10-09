import numpy as np
from alignment.constitutional_ai import (
    critique,
    generate_responses,
    revise,
    train_on_revisions,
)


class TestConstitutionalAI:
    def test_generate_responses_probabilities(self):
        prompt_emb = np.random.randn(4, 8)
        resp = generate_responses(prompt_emb)
        assert np.allclose(np.sum(resp, axis=-1), 1.0)

    def test_critique_high_entropy(self):
        uniform = np.ones((2, 4)) / 4.0
        mask = critique(uniform, threshold=0.3)
        assert np.all(~mask)

    def test_critique_low_entropy(self):
        low_ent = np.array([[0.99, 0.01, 0.0, 0.0]])
        mask = critique(low_ent, threshold=0.3)
        assert np.all(mask)

    def test_revise_shape(self):
        original = np.ones((2, 4)) / 4.0
        mask = np.array([True, False])
        revised = revise(original, mask, temperature=0.5)
        assert revised.shape == original.shape
        assert np.allclose(np.sum(revised, axis=-1), 1.0)

    def test_train_on_revisions_zero(self):
        a = np.random.randn(10, 4)
        mse = train_on_revisions(a, a)
        assert np.isclose(mse, 0.0)
