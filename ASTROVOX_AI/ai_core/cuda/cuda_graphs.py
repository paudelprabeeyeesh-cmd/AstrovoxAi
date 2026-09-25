from typing import Optional, List, Dict, Any
import torch
import torch.cuda as cuda


class CUDAGraphManager:
    def __init__(self, device: int = 0):
        self.device = device
        self.graphs: Dict[str, Any] = {}
        self.graph_pools: Dict[str, cuda.CUDAPool] = {}

    def capture_graph(self, fn: callable, static_inputs: Dict[str, torch.Tensor], name: str) -> None:
        stream = cuda.Stream(device=self.device)
        stream.wait_stream(cuda.current_stream(self.device))
        with stream:
            fn(**static_inputs)
        stream.synchronize()
        g = torch.cuda.CUDAGraph()
        with torch.cuda.graph(g, stream=stream):
            fn(**static_inputs)
        self.graphs[name] = {'graph': g, 'inputs': static_inputs, 'stream': stream}

    def replay(self, name: str) -> None:
        if name in self.graphs:
            self.graphs[name]['graph'].replay()

    def capture_full_model(self, model: torch.nn.Module, dummy_input: torch.Tensor, name: str) -> None:
        stream = cuda.Stream()
        stream.wait_stream(cuda.current_stream())
        model.eval()
        with stream:
            model(dummy_input)
        stream.synchronize()
        g = torch.cuda.CUDAGraph()
        with torch.cuda.graph(g, stream=stream):
            model(dummy_input)
        self.graphs[name] = {'graph': g, 'inputs': {'input': dummy_input}, 'stream': stream}

    def clear(self) -> None:
        self.graphs.clear()
