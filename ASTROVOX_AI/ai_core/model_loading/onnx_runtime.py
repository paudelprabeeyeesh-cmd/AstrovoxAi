from typing import Optional, Dict, Any, List
import torch
import torch.nn as nn
import onnxruntime as ort
from pathlib import Path


class ONNXRuntimeLoader:
    def __init__(self, model_path: str, providers: Optional[List[str]] = None):
        self.model_path = model_path
        self.providers = providers or ['CPUExecutionProvider']
        self.session = ort.InferenceSession(model_path, providers=self.providers)
        self.input_names = [inp.name for inp in self.session.get_inputs()]
        self.output_names = [out.name for out in self.session.get_outputs()]

    def infer(self, inputs: Dict[str, torch.Tensor]) -> List[torch.Tensor]:
        ort_inputs = {name: tensor.cpu().numpy() for name, tensor in inputs.items()}
        outputs = self.session.run(self.output_names, ort_inputs)
        return [torch.tensor(output) for output in outputs]

    def get_input_details(self) -> List[Dict[str, Any]]:
        return [{'name': inp.name, 'shape': inp.shape, 'type': inp.type} for inp in self.session.get_inputs()]

    def get_output_details(self) -> List[Dict[str, Any]]:
        return [{'name': out.name, 'shape': out.shape, 'type': out.type} for out in self.session.get_outputs()]


class ONNXExporter:
    @staticmethod
    def export(model: nn.Module, dummy_input: torch.Tensor, path: str, opset: int = 17) -> None:
        torch.onnx.export(model, dummy_input, path, opset_version=opset, input_names=['input'], output_names=['output'], dynamic_axes={'input': {0: 'batch', 1: 'seq'}, 'output': {0: 'batch', 1: 'seq'}})
