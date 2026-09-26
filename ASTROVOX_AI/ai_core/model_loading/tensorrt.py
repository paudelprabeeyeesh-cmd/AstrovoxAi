from typing import Dict, List
import torch
import torch.nn as nn


class TensorRTLoader:
    def __init__(self, engine_path: str, device: str = 'cuda'):
        self.engine_path = engine_path
        self.device = device
        try:
            import tensorrt as trt
            self.trt = trt
            self.logger = trt.Logger(trt.Logger.INFO)
            with open(engine_path, 'rb') as f:
                runtime = trt.Runtime(self.logger)
                self.engine = runtime.deserialize_cuda_engine(f.read())
            self.context = self.engine.create_execution_context()
            self.stream = torch.cuda.Stream()
            self.input_names = [self.engine.get_binding_name(i) for i in range(self.engine.num_bindings) if self.engine.binding_is_input(i)]
            self.output_names = [self.engine.get_binding_name(i) for i in range(self.engine.num_bindings) if not self.engine.binding_is_input(i)]
        except ImportError:
            raise ImportError('TensorRT is not installed')

    def infer(self, inputs: Dict[str, torch.Tensor]) -> List[torch.Tensor]:
        bindings = []
        for name in self.input_names:
            assert name in inputs, f'Missing input: {name}'
            tensor = inputs[name].contiguous()
            bindings.append(tensor.data_ptr())
        output_tensors = []
        for name in self.output_names:
            shape = self.context.get_binding_shape(self.engine.get_binding_index(name))
            dtype = torch.float32
            tensor = torch.empty(tuple(shape), dtype=dtype, device=self.device)
            output_tensors.append(tensor)
            bindings.append(tensor.data_ptr())
        self.context.execute_async_v2(bindings, self.stream.cuda_stream)
        self.stream.synchronize()
        return output_tensors

    @staticmethod
    def build_engine(model: nn.Module, dummy_input: torch.Tensor, path: str, fp16: bool = False) -> None:
        import tensorrt as trt
        logger = trt.Logger(trt.Logger.INFO)
        builder = trt.Builder(logger)
        network_flags = 1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
        network = builder.create_network(network_flags)
        parser = trt.OnnxParser(network, logger)
        with open(path.replace('.engine', '.onnx'), 'rb') as f:
            parser.parse(f.read())
        config = builder.create_builder_config()
        if fp16:
            config.set_flag(trt.BuilderFlag.FP16)
        serialized_engine = builder.build_serialized_network(network, config)
        with open(path, 'wb') as f:
            f.write(serialized_engine)
