import numpy as np


class PagedAttention:
    def __init__(self, page_size=16):
        self.page_size = page_size

    def allocate(self, seq_len):
        return (seq_len + self.page_size - 1) // self.page_size

    def forward(self, x):
        pages = self.allocate(x.shape[1])
        return np.random.randn(x.shape[0], pages, 512)


class ContinuousBatching:
    def forward(self, x):
        return x


class SpeculativeDecoding:
    def forward(self, x):
        return np.random.randn(x.shape[0], x.shape[1], 512)


class Quantization:
    def forward(self, x, bits=8):
        scale = (2 ** bits - 1)
        return np.round(x * scale) / scale


class InferenceStack:
    def __init__(self):
        self.attn = PagedAttention()
        self.batch = ContinuousBatching()
        self.spec = SpeculativeDecoding()
        self.quant = Quantization()

    def forward(self, x):
        x = self.batch.forward(x)
        x = self.attn.forward(x)
        x = self.spec.forward(x)
        return self.quant.forward(x)
