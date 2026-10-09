from model_architecture.attention import MultiHeadAttention


class TestMultiHeadAttention:
    def test_output_shape(self):
        B, T, C = 2, 10, 64
        model = MultiHeadAttention(d_model=C, num_heads=4)
        x = [[[0.1 for _ in range(C)] for _ in range(T)] for _ in range(B)]
        out = model.forward(x)
        assert len(out) == B
        assert len(out[0]) == T
        assert len(out[0][0]) == C

    def test_with_mask(self):
        B, T, C = 2, 10, 64
        model = MultiHeadAttention(d_model=C, num_heads=4)
        x = [[[0.1 for _ in range(C)] for _ in range(T)] for _ in range(B)]
        mask = [[j > i for j in range(T)] for i in range(T)]
        out = model.forward(x, mask=mask)
        assert len(out) == B
        assert len(out[0]) == T
        assert len(out[0][0]) == C
