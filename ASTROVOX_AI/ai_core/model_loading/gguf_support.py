from typing import Dict
import torch
import torch.nn as nn
import struct
import numpy as np


class GGUFFile:
    def __init__(self, path: str):
        self.path = path
        self.header = {}
        self.tensors: Dict[str, torch.Tensor] = {}

    def load(self) -> Dict[str, torch.Tensor]:
        with open(self.path, 'rb') as f:
            magic = f.read(4)
            if magic != b'GGUF':
                raise ValueError('Invalid GGUF magic bytes')
            self._parse_header(f)
            self._parse_tensors(f)
        return self.tensors

    def _parse_header(self, f) -> None:
        version = struct.unpack('<I', f.read(4))[0]
        tensor_count = struct.unpack('<Q', f.read(8))[0]
        metadata_count = struct.unpack('<Q', f.read(8))[0]
        self.header = {'version': version, 'tensor_count': tensor_count, 'metadata_count': metadata_count}

    def _parse_tensors(self, f) -> None:
        for _ in range(self.header.get('tensor_count', 0)):
            name_len = struct.unpack('<Q', f.read(8))[0]
            name = f.read(name_len).decode('utf-8')
            dims = struct.unpack('<I', f.read(4))[0]
            shape = struct.unpack(f'<{dims}Q', f.read(8 * dims))
            dtype, offset = struct.unpack('<IQ', f.read(4 + 8))
            tensor = self._load_tensor_data(f, shape, dtype, offset)
            self.tensors[name] = tensor

    def _load_tensor_data(self, f, shape: tuple, dtype: int, offset: int) -> torch.Tensor:
        f.seek(offset)
        dtype_map = {0: torch.float32, 1: torch.float16, 2: torch.int8, 3: torch.int32, 4: torch.float64}
        torch_dtype = dtype_map.get(dtype, torch.float32)
        data = np.fromfile(f, dtype=np.dtype(torch_dtype).type, count=int(np.prod(shape)))
        return torch.tensor(data, dtype=torch_dtype).reshape(shape)


class GGUFSaver:
    @staticmethod
    def save(model: nn.Module, path: str) -> None:
        state_dict = model.state_dict()
        with open(path, 'wb') as f:
            f.write(b'GGUF')
            f.write(struct.pack('<I', 3))
            tensor_count = len(state_dict)
            f.write(struct.pack('<Q', tensor_count))
            f.write(struct.pack('<Q', 0))
            for name, tensor in state_dict.items():
                f.write(struct.pack('<Q', len(name)))
                f.write(name.encode('utf-8'))
                f.write(struct.pack('<I', len(tensor.shape)))
                for dim in tensor.shape:
                    f.write(struct.pack('<Q', dim))
                dtype = {torch.float32: 0, torch.float16: 1, torch.int8: 2, torch.int32: 3, torch.float64: 4}.get(tensor.dtype, 0)
                offset = f.tell() + 4 + 8
                f.write(struct.pack('<IQ', dtype, offset))
                tensor.numpy().tofile(f)
