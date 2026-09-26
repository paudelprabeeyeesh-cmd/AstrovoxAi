from typing import List
import torch


class KVCache:
    def __init__(self, max_batch_size: int, max_seq_len: int, num_heads: int, head_dim: int, device: str = "cuda", dtype: torch.dtype = torch.float16):
        self.max_batch_size = max_batch_size
        self.max_seq_len = max_seq_len
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.device = device
        self.dtype = dtype
        self.k_cache = torch.zeros(max_batch_size, num_heads, max_seq_len, head_dim, device=device, dtype=dtype)
        self.v_cache = torch.zeros(max_batch_size, num_heads, max_seq_len, head_dim, device=device, dtype=dtype)
        self.current_len = torch.zeros(max_batch_size, dtype=torch.long, device=device)

    def append(self, k: torch.Tensor, v: torch.Tensor, batch_idx: int) -> None:
        pos = self.current_len[batch_idx].item()
        self.k_cache[batch_idx, :, pos, :] = k
        self.v_cache[batch_idx, :, pos, :] = v
        self.current_len[batch_idx] = pos + 1

    def get(self, batch_idx: int) -> tuple:
        length = self.current_len[batch_idx].item()
        return self.k_cache[batch_idx, :, :length, :], self.v_cache[batch_idx, :, :length, :]

    def get_all(self) -> tuple:
        return self.k_cache, self.v_cache

    def reset(self) -> None:
        self.k_cache.zero_()
        self.v_cache.zero_()
        self.current_len.zero_()

    def to(self, device: str) -> "KVCache":
        self.k_cache = self.k_cache.to(device)
        self.v_cache = self.v_cache.to(device)
        self.current_len = self.current_len.to(device)
        self.device = device
        return self


class PagedKVCache:
    def __init__(self, num_blocks: int, block_size: int, num_heads: int, head_dim: int, device: str = "cuda", dtype: torch.dtype = torch.float16):
        self.num_blocks = num_blocks
        self.block_size = block_size
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.device = device
        self.dtype = dtype
        self.k_cache = torch.zeros(num_blocks, num_heads, block_size, head_dim, device=device, dtype=dtype)
        self.v_cache = torch.zeros(num_blocks, num_heads, block_size, head_dim, device=device, dtype=dtype)
        self.block_table = {}
        self.free_blocks = list(range(num_blocks))

    def allocate(self, batch_idx: int, num_blocks: int) -> List[int]:
        blocks = self.free_blocks[:num_blocks]
        self.free_blocks = self.free_blocks[num_blocks:]
        self.block_table[batch_idx] = blocks
        return blocks

    def append(self, k: torch.Tensor, v: torch.Tensor, batch_idx: int, offset: int = 0) -> None:
        blocks = self.block_table.get(batch_idx, [])
        if not blocks:
            blocks = self.allocate(batch_idx, 1)
        block_idx = blocks[0]
        block_offset = offset % self.block_size
        self.k_cache[block_idx, :, block_offset, :] = k
        self.v_cache[block_idx, :, block_offset, :] = v

    def get(self, batch_idx: int, start: int, length: int) -> tuple:
        blocks = self.block_table.get(batch_idx, [])
        if not blocks:
            return torch.empty(self.num_heads, 0, self.head_dim, device=self.device, dtype=self.dtype), torch.empty(self.num_heads, 0, self.head_dim, device=self.device, dtype=self.dtype)
        block_idx = blocks[0]
        return self.k_cache[block_idx, :, start:start + length, :], self.v_cache[block_idx, :, start:start + length, :]

    def free(self, batch_idx: int) -> None:
        blocks = self.block_table.pop(batch_idx, [])
        self.free_blocks.extend(blocks)


class KVCacheCompressor:
    def __init__(self, compression_ratio: float = 0.5, method: str = "mean"):
        self.compression_ratio = compression_ratio
        self.method = method

    def compress(self, k: torch.Tensor, v: torch.Tensor) -> tuple:
        if self.compression_ratio >= 1.0:
            return k, v
        B, H, T, D = k.shape
        compressed_T = max(1, int(T * self.compression_ratio))
        if self.method == "mean":
            k_compressed = k.mean(dim=2, keepdim=True).expand(B, H, compressed_T, D)
            v_compressed = v.mean(dim=2, keepdim=True).expand(B, H, compressed_T, D)
        elif self.method == "random":
            indices = torch.randperm(T, device=k.device)[:compressed_T].sort()[0]
            k_compressed = k[:, :, indices, :]
            v_compressed = v[:, :, indices, :]
        else:
            k_compressed = k[:, :, -compressed_T:, :]
            v_compressed = v[:, :, -compressed_T:, :]
        return k_compressed, v_compressed
