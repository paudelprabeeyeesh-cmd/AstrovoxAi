import random


class FeedForward:
    def __init__(self, d_model, d_ff=None):
        if d_ff is None:
            d_ff = d_model * 4
        self.W1 = [[random.gauss(0, 0.02) for _ in range(d_ff)] for _ in range(d_model)]
        self.W2 = [[random.gauss(0, 0.02) for _ in range(d_model)] for _ in range(d_ff)]
        self.b1 = [0.0] * d_ff
        self.b2 = [0.0] * d_model

    def forward(self, x):
        out = []
        for b in range(len(x)):
            batch_out = []
            for t in range(len(x[0])):
                hidden = [sum(x[b][t][i] * self.W1[i][j] for i in range(len(self.W1))) + self.b1[j] for j in range(len(self.b1))]
                activated = [max(0.0, h) for h in hidden]
                out_vec = [sum(activated[i] * self.W2[i][j] for i in range(len(self.W2))) + self.b2[j] for j in range(len(self.b2))]
                batch_out.append(out_vec)
            out.append(batch_out)
        return out
