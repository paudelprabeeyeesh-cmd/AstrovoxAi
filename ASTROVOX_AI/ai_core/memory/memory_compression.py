import torch


class MemoryCompressor:
    def __init__(self, compression_ratio: float = 0.5, method: str = 'mean'):
        self.compression_ratio = compression_ratio
        self.method = method

    def compress(self, memory: torch.Tensor) -> torch.Tensor:
        if self.method == 'mean':
            return self._mean_compress(memory)
        elif self.method == 'pca':
            return self._pca_compress(memory)
        elif self.method == 'quantize':
            return self._quantize_compress(memory)
        return memory

    def decompress(self, compressed: torch.Tensor, original_shape: tuple) -> torch.Tensor:
        if self.method == 'mean':
            return compressed.repeat_interleave(original_shape[0] // compressed.shape[0], dim=0)
        return compressed

    def _mean_compress(self, memory: torch.Tensor) -> torch.Tensor:
        compressed_size = max(1, int(memory.shape[0] * self.compression_ratio))
        return memory[:compressed_size].mean(dim=0, keepdim=True).repeat(compressed_size, 1)

    def _pca_compress(self, memory: torch.Tensor) -> torch.Tensor:
        memory_centered = memory - memory.mean(dim=0, keepdim=True)
        _, _, V = torch.svd(memory_centered)
        components = V[:, :max(1, int(memory.shape[1] * self.compression_ratio))]
        return memory_centered @ components

    def _quantize_compress(self, memory: torch.Tensor) -> torch.Tensor:
        scale = memory.abs().max() / 127.0
        return (memory / scale).round().clamp(-128, 127).to(torch.int8)
