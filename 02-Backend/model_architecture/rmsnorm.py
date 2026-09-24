import math


class RMSNorm:
    def __init__(self, d_model, eps=1e-6):
        self.gamma = [1.0] * d_model
        self.eps = eps

    def forward(self, x):
        out = []
        for b in range(len(x)):
            batch_out = []
            for t in range(len(x[0])):
                row = x[b][t]
                rms = math.sqrt(sum(v * v for v in row) / len(row) + self.eps)
                batch_out.append([(v / rms) * g for v, g in zip(row, self.gamma)])
            out.append(batch_out)
        return out
