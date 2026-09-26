from typing import Optional
import torch
import torch.nn as nn


class CUDAFusedOp:
    @staticmethod
    def fused_linear_gelu(x: torch.Tensor, weight: torch.Tensor, bias: Optional[torch.Tensor] = None) -> torch.Tensor:
        out = torch.addmm(bias if bias is not None else torch.zeros(weight.size(0), device=x.device, dtype=x.dtype), x, weight.t())
        return torch.nn.functional.gelu(out)

    @staticmethod
    def fused_linear_relu(x: torch.Tensor, weight: torch.Tensor, bias: Optional[torch.Tensor] = None) -> torch.Tensor:
        out = torch.addmm(bias if bias is not None else torch.zeros(weight.size(0), device=x.device, dtype=x.dtype), x, weight.t())
        return torch.relu(out)

    @staticmethod
    def fused_rms_norm(x: torch.Tensor, weight: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
        variance = x.pow(2).mean(-1, keepdim=True)
        x = x * torch.rsqrt(variance + eps)
        return weight * x

    @staticmethod
    def fused_attn_qkv(x: torch.Tensor, q_proj: nn.Linear, k_proj: nn.Linear, v_proj: nn.Linear) -> tuple:
        q = q_proj(x)
        k = k_proj(x)
        v = v_proj(x)
        return q, k, v

    @staticmethod
    def fused_dropout_residual(x: torch.Tensor, residual: torch.Tensor, dropout: float = 0.1, training: bool = True) -> torch.Tensor:
        return torch.nn.functional.dropout(x, p=dropout, training=training) + residual


class CUDAGraphFusion:
    def __init__(self, model: nn.Module, device: int = 0):
        self.model = model
        self.device = device
        self.graphs: Dict[str, Any] = {}

    def create_fused_graph(self, name: str, input_shapes: Dict[str, tuple]) -> None:
        dummy_inputs = {k: torch.zeros(v, device=f'cuda:{self.device}') for k, v in input_shapes.items()}
        stream = torch.cuda.Stream(device=self.device)
        with stream:
            self.model(**dummy_inputs)
        stream.synchronize()
        g = torch.cuda.CUDAGraph()
        with torch.cuda.graph(g, stream=stream):
            self.model(**dummy_inputs)
        self.graphs[name] = {'graph': g, 'inputs': dummy_inputs}
