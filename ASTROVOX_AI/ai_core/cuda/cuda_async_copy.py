from typing import Optional
import torch
import torch.cuda as cuda
from torch.cuda import Stream, Event

try:
    import triton
    import triton.language as tl
    TRITON_AVAILABLE = True
except ImportError:
    TRITON_AVAILABLE = False


class CUDAAsyncCopy:
    def __init__(self, device: int = 0, num_streams: int = 2):
        self.device = device
        self.num_streams = num_streams
        self.streams = [Stream(device=device) for _ in range(num_streams)]
        self.events = [Event(device=device) for _ in range(num_streams)]
        self.current_stream_idx = 0

    def get_stream(self) -> Stream:
        stream = self.streams[self.current_stream_idx]
        self.current_stream_idx = (self.current_stream_idx + 1) % self.num_streams
        return stream

    def async_copy_h2d(self, host_tensor: torch.Tensor, device_tensor: torch.Tensor, stream: Optional[Stream] = None) -> None:
        stream = stream or self.get_stream()
        with stream:
            device_tensor.copy_(host_tensor, non_blocking=True)

    def async_copy_d2h(self, device_tensor: torch.Tensor, host_tensor: torch.Tensor, stream: Optional[Stream] = None) -> None:
        stream = stream or self.get_stream()
        with stream:
            host_tensor.copy_(device_tensor, non_blocking=True)

    def async_copy_d2d(self, src: torch.Tensor, dst: torch.Tensor, stream: Optional[Stream] = None) -> None:
        stream = stream or self.get_stream()
        with stream:
            dst.copy_(src, non_blocking=True)

    def record_event(self, stream: Optional[Stream] = None) -> Event:
        stream = stream or self.streams[0]
        event = Event(device=self.device)
        stream.record_event(event)
        return event

    def wait_event(self, stream: Stream, event: Event) -> None:
        stream.wait_event(event)

    def synchronize(self) -> None:
        for stream in self.streams:
            stream.synchronize()

    def prefetch(self, tensor: torch.Tensor, device: int) -> None:
        cuda.prefetch(tensor, device)

    def memcpy_async(self, src: torch.Tensor, dst: torch.Tensor, stream: Optional[Stream] = None) -> None:
        stream = stream or self.get_stream()
        with stream:
            dst.copy_(src, non_blocking=True)


if TRITON_AVAILABLE:
    @triton.jit
    def _async_copy_kernel(
        src_ptr, dst_ptr,
        M, N,
        src_stride_m, src_stride_n,
        dst_stride_m, dst_stride_n,
        BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    ):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        mask = (rm[:, None] < M) & (rn[None, :] < N)
        src = tl.load(src_ptr + rm[:, None] * src_stride_m + rn[None, :] * src_stride_n, mask=mask, other=0.0)
        tl.atomic_max(dst_ptr + rm[:, None] * dst_stride_m + rn[None, :] * dst_stride_n, src, mask=mask)

    def async_copy_triton(src: torch.Tensor, dst: torch.Tensor) -> torch.Tensor:
        M, N = src.shape
        BLOCK_M, BLOCK_N = 16, 16
        grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
        _async_copy_kernel[grid](
            src, dst,
            M, N,
            src.stride(0), src.stride(1),
            dst.stride(0), dst.stride(1),
            BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        )
        return dst


class CUDAPinnedMemoryCopy:
    def __init__(self, device: int = 0):
        self.device = device
        self.stream = Stream(device=device)
        self.event = Event(device=device)

    def copy_async(self, host_tensor: torch.Tensor, device_tensor: torch.Tensor) -> None:
        host_pinned = host_tensor.pin_memory()
        with self.stream:
            device_tensor.copy_(host_pinned, non_blocking=True)
        self.stream.record_event(self.event)

    def wait(self) -> None:
        self.event.synchronize()
