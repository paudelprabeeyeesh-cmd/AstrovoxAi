import math
import random


def _matmul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(len(B))) for j in range(len(B[0]))] for i in range(len(A))]


def _softmax_rows(M):
    out = []
    for row in M:
        max_val = max(row)
        exps = [math.exp(x - max_val) for x in row]
        s = sum(exps)
        out.append([e / s for e in exps])
    return out


class MultiHeadAttention:
    def __init__(self, d_model, num_heads):
        self.d_model = d_model
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads
        assert d_model % num_heads == 0

        self.W_q = [[random.gauss(0, 0.02) for _ in range(d_model)] for _ in range(d_model)]
        self.W_k = [[random.gauss(0, 0.02) for _ in range(d_model)] for _ in range(d_model)]
        self.W_v = [[random.gauss(0, 0.02) for _ in range(d_model)] for _ in range(d_model)]
        self.W_o = [[random.gauss(0, 0.02) for _ in range(d_model)] for _ in range(d_model)]
        self.scale = self.head_dim ** -0.5

    def forward(self, x, mask=None):
        B = len(x)
        T = len(x[0])
        C = self.d_model

        q = [_matmul(x[b], self.W_q) for b in range(B)]
        k = [_matmul(x[b], self.W_k) for b in range(B)]
        v = [_matmul(x[b], self.W_v) for b in range(B)]

        q_heads = [[[q[b][t][h * self.head_dim:(h + 1) * self.head_dim] for h in range(self.num_heads)] for t in range(T)] for b in range(B)]
        k_heads = [[[k[b][t][h * self.head_dim:(h + 1) * self.head_dim] for h in range(self.num_heads)] for t in range(T)] for b in range(B)]
        v_heads = [[[v[b][t][h * self.head_dim:(h + 1) * self.head_dim] for h in range(self.num_heads)] for t in range(T)] for b in range(B)]

        q_t = [[[q_heads[b][t][h] for t in range(T)] for h in range(self.num_heads)] for b in range(B)]
        k_t = [[[k_heads[b][t][h] for t in range(T)] for h in range(self.num_heads)] for b in range(B)]
        v_t = [[[v_heads[b][t][h] for t in range(T)] for h in range(self.num_heads)] for b in range(B)]

        scores = []
        for b in range(B):
            batch_scores = []
            for h in range(self.num_heads):
                head_scores = []
                for t_q in range(T):
                    row = []
                    for t_k in range(T):
                        dot = sum(q_t[b][h][t_q][i] * k_t[b][h][t_k][i] for i in range(self.head_dim))
                        row.append(dot * self.scale)
                    head_scores.append(row)
                batch_scores.append(head_scores)
            scores.append(batch_scores)

        if mask is not None:
            for b in range(B):
                for h in range(self.num_heads):
                    for i in range(T):
                        for j in range(T):
                            if mask[i][j] == 0:
                                scores[b][h][i][j] = -1e9

        attn = []
        for b in range(B):
            batch_attn = []
            for h in range(self.num_heads):
                batch_attn.append(_softmax_rows(scores[b][h]))
            attn.append(batch_attn)

        out = []
        for b in range(B):
            batch_out = []
            for h in range(self.num_heads):
                head_out = []
                for t in range(T):
                    vec = [0.0] * self.head_dim
                    for t_k in range(T):
                        a = attn[b][h][t][t_k]
                        for i in range(self.head_dim):
                            vec[i] += a * v_t[b][h][t_k][i]
                    head_out.append(vec)
                batch_out.append(head_out)
            out.append(batch_out)

        final = []
        for b in range(B):
            batch_final = []
            for t in range(T):
                vec = []
                for h in range(self.num_heads):
                    vec.extend(out[b][h][t])
                batch_final.append(vec)
            final.append(batch_final)

        final = [_matmul(final[b], self.W_o) for b in range(B)]
        return final
