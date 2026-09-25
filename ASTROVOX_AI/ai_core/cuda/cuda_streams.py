from typing import List, Optional
import torch
import torch.cuda as cuda


class CUDAStreamManager:
    def __init__(self, num_streams: int = 4, device: int = 0):
        self.device = device
        self.streams = [cuda.Stream(device=device) for _ in range(num_streams)]
        self.current_stream_idx = 0

    def get_stream(self) -> cuda.Stream:
        stream = self.streams[self.current_stream_idx]
        self.current_stream_idx = (self.current_stream_idx + 1) % len(self.streams)
        return stream

    def stream_wait(self, stream: cuda.Stream, event: cuda.Event) -> None:
        stream.wait_event(event)

    def record_event(self, stream: cuda.Stream) -> cuda.Event:
        event = cuda.Event()
        stream.record_event(event)
        return event

    def synchronize(self) -> None:
        for stream in self.streams:
            stream.synchronize()

    def synchronize_stream(self, stream: cuda.Stream) -> None:
        stream.synchronize()
