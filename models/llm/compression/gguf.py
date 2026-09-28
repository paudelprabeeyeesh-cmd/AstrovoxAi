from __future__ import annotations

import io
import json
import logging
import pickle
from typing import Any

import torch

from models.llm.quantization import _has_gguf, logger


def export_gguf(
    model: torch.nn.Module,
    path: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    if _has_gguf():
        import gguf

        state_dict = model.state_dict()
        gguf_writer = gguf.GGUFWriter(path, "llm")
        if metadata:
            for k, v in metadata.items():
                gguf_writer.add_kv_data(k, v)
        for tensor_name, tensor in state_dict.items():
            gguf_writer.add_tensor(tensor_name, tensor.cpu().numpy())
        gguf_writer.write_header_to_file()
        gguf_writer.write_kv_data_to_file()
        gguf_writer.write_tensors_to_file()
        gguf_writer.close()
        return

    state_dict = model.state_dict()
    metadata = metadata or {}
    data = {
        "metadata": metadata,
        "tensors": {
            k: {"dtype": str(v.dtype), "shape": list(v.shape)}
            for k, v in state_dict.items()
        },
    }
    with open(path, "wb") as f:
        pickle.dump(data, f)


def import_gguf(
    path: str,
) -> tuple[dict[str, Any], dict[str, torch.Tensor]]:
    if _has_gguf():
        import gguf

        reader = gguf.GGUFReader(path)
        metadata = {k: reader.metadata[k] for k in reader.metadata}
        tensors = {
            name: torch.tensor(reader.get_tensor(name))
            for name in reader.tensor_names
        }
        return metadata, tensors

    with open(path, "rb") as f:
        data = pickle.load(f)
    tensors = {
        k: torch.zeros(v["shape"], dtype=v["dtype"])
        for k, v in data["tensors"].items()
    }
    return data["metadata"], tensors


def update_gguf_metadata(
    path: str,
    metadata: dict[str, Any],
) -> None:
    if _has_gguf():
        import gguf

        reader = gguf.GGUFReader(path)
        existing = dict(reader.metadata)
        existing.update(metadata)
        state_dict = {
            name: torch.tensor(reader.get_tensor(name))
            for name in reader.tensor_names
        }
        gguf_writer = gguf.GGUFWriter(path, "llm")
        for k, v in existing.items():
            gguf_writer.add_kv_data(k, v)
        for tensor_name, tensor in state_dict.items():
            gguf_writer.add_tensor(tensor_name, tensor.cpu().numpy())
        gguf_writer.write_header_to_file()
        gguf_writer.write_kv_data_to_file()
        gguf_writer.write_tensors_to_file()
        gguf_writer.close()
        return

    with open(path, "rb") as f:
        data = pickle.load(f)
    data["metadata"].update(metadata)
    with open(path, "wb") as f:
        pickle.dump(data, f)
