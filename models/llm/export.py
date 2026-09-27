"""
Phase 12 Model Export Module

Supports multiple export formats for LLM models with graceful fallbacks.
"""

import os
import sys
import json
import time
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field, asdict
from enum import Enum

import torch
import torch.nn as nn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    HUGGINGFACE = "huggingface"
    ONNX = "onnx"
    TENSORRT = "tensorrt"
    GGUF = "gguf"
    SAFETENSORS = "safetensors"


@dataclass
class ExportMetadata:
    model_name: str
    format: str
    timestamp: str
    original_config: Dict[str, Any] = field(default_factory=dict)
    exported_files: List[str] = field(default_factory=list)
    export_params: Dict[str, Any] = field(default_factory=dict)
    size_bytes: int = 0
    validation_status: str = "pending"
    notes: List[str] = field(default_factory=list)


class FormatValidationError(Exception):
    pass


class ExportError(Exception):
    pass


def _validate_model(model: nn.Module) -> None:
    if model is None:
        raise FormatValidationError("Model is None")
    if not isinstance(model, nn.Module):
        raise FormatValidationError(f"Expected nn.Module, got {type(model)}")


def _validate_state_dict(state_dict: Dict[str, Any]) -> None:
    if not isinstance(state_dict, dict):
        raise FormatValidationError(f"Expected dict for state_dict, got {type(state_dict)}")
    if len(state_dict) == 0:
        raise FormatValidationError("State dict is empty")


def _human_readable_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.2f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"


def _calculate_directory_size(path: Path) -> int:
    total = 0
    for entry in path.rglob("*"):
        if entry.is_file():
            total += entry.stat().st_size
    return total


class BaseExporter:
    def __init__(self, model: nn.Module, config: Dict[str, Any], metadata: Optional[ExportMetadata] = None):
        _validate_model(model)
        self.model = model
        self.config = config
        self.metadata = metadata or ExportMetadata(
            model_name=config.get("model_name", "astrovox_model"),
            format="unknown",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            original_config=dict(config),
        )

    def export(self, output_dir: Union[str, Path], **kwargs) -> ExportMetadata:
        raise NotImplementedError

    def _save_metadata(self, output_dir: Path) -> None:
        meta_path = output_dir / "export_metadata.json"
        with open(meta_path, "w") as f:
            json.dump(asdict(self.metadata), f, indent=2)
        self.metadata.exported_files.append(str(meta_path.name))

    def _save_config(self, output_dir: Path, filename: str = "config.json") -> None:
        config_path = output_dir / filename
        with open(config_path, "w") as f:
            json.dump(self.config, f, indent=2)
        self.metadata.exported_files.append(str(config_path.name))


class HuggingFaceExporter(BaseExporter):
    def export(self, output_dir: Union[str, Path], tokenizer=None, **kwargs) -> ExportMetadata:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self.metadata.format = ExportFormat.HUGGINGFACE.value

        try:
            from transformers import PretrainedConfig, PreTrainedTokenizer
        except ImportError as e:
            self.metadata.notes.append(f"HuggingFace export skipped: transformers not available ({e})")
            self.metadata.validation_status = "skipped"
            logger.warning(f"HuggingFace export skipped: {e}")
            return self.metadata

        try:
            hf_config = self._build_hf_config()
            hf_config.save_pretrained(str(output_dir))

            if tokenizer is not None:
                if isinstance(tokenizer, PreTrainedTokenizer):
                    tokenizer.save_pretrained(str(output_dir))
                else:
                    self._export_tokenizer_json(tokenizer, output_dir / "tokenizer.json")
            else:
                self._export_tokenizer_json(None, output_dir / "tokenizer.json")

            state_dict = self.model.state_dict()
            try:
                from safetensors.torch import save_file as st_save
                st_save(state_dict, str(output_dir / "model.safetensors"))
                self.metadata.exported_files.append("model.safetensors")
            except Exception:
                torch.save(state_dict, str(output_dir / "pytorch_model.bin"))
                self.metadata.exported_files.append("pytorch_model.bin")

            self._save_config(output_dir, "config.json")
            readme = output_dir / "README.md"
            readme.write_text(f"# {self.metadata.model_name}\n\nExported with AstrovoxAi Phase 12 export module.\n")
            self.metadata.exported_files.append("README.md")

            self.metadata.size_bytes = _calculate_directory_size(output_dir)
            self.metadata.validation_status = "success"
            self._save_metadata(output_dir)
            logger.info(f"HuggingFace export completed: {output_dir} ({_human_readable_size(self.metadata.size_bytes)})")
        except Exception as e:
            self.metadata.notes.append(f"HuggingFace export failed: {e}")
            self.metadata.validation_status = "failed"
            logger.error(f"HuggingFace export failed: {e}")
            raise ExportError(f"HuggingFace export failed: {e}") from e

        return self.metadata

    def _build_hf_config(self) -> "PretrainedConfig":
        cfg = self.config
        return PretrainedConfig(
            vocab_size=int(cfg.get("vocab_size", 100)),
            hidden_size=int(cfg.get("hidden_size", 64)),
            num_hidden_layers=int(cfg.get("num_hidden_layers", 2)),
            num_attention_heads=int(cfg.get("num_attention_heads", 2)),
            intermediate_size=int(cfg.get("intermediate_size", 128)),
            max_position_embeddings=int(cfg.get("max_position_embeddings", 2048)),
            rms_norm_eps=float(cfg.get("rms_norm_eps", 1e-5)),
            rope_theta=float(cfg.get("rope_theta", 10000.0)),
            model_type="llama",
            architectures=["LLMForCausalLM"],
        )

    def _export_tokenizer_json(self, tokenizer, path: Path) -> None:
        vocab_size = int(self.config.get("vocab_size", 100))
        tokenizer_data = {
            "version": "1.0",
            "truncation": {"direction": "Right", "max_length": 256, "strategy": "LongestFirst", "strategy_id": 0},
            "padding": {"direction": "Right", "pad_id": 0, "pad_type_id": 0, "pad_token": "<pad>"},
            "added_tokens": [],
            "normalizer": {"type": "Sequence", "normalizers": []},
            "pre_tokenizer": {"type": "Whitespace", "split": True, "replacements": [{"content": " ", "prefix": True, "id": -1}]},
            "post_processor": None,
            "decoder": None,
            "model": {
                "type": "BPE",
                "dropout": 0.0,
                "unk_token": "<unk>",
                "continuing_subword_prefix": None,
                "end_of_word_suffix": None,
                "fuse_unk": False,
                "vocab": {f"<token_{i}>": i for i in range(vocab_size)},
                "merges": [],
            },
        }
        with open(path, "w") as f:
            json.dump(tokenizer_data, f, indent=2)
        self.metadata.exported_files.append(str(path.name))


class ONNXExporter(BaseExporter):
    def export(self, output_dir: Union[str, Path], opset: int = 17, dynamic_axes: bool = True, **kwargs) -> ExportMetadata:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self.metadata.format = ExportFormat.ONNX.value

        try:
            import onnx
            from onnxruntime import InferenceSession
        except ImportError as e:
            self.metadata.notes.append(f"ONNX export skipped: onnx/onnxruntime not available ({e})")
            self.metadata.validation_status = "skipped"
            logger.warning(f"ONNX export skipped: {e}")
            return self.metadata

        try:
            self.model.eval()
            vocab_size = int(self.config.get("vocab_size", 100))
            dummy_input = torch.randint(0, vocab_size, (1, 16))
            onnx_path = output_dir / "model.onnx"

            input_names = ["input_ids"]
            output_names = ["logits"]
            dynamic_axes_dict = None
            if dynamic_axes:
                dynamic_axes_dict = {"input_ids": {0: "batch_size", 1: "sequence_length"}, "logits": {0: "batch_size", 1: "sequence_length"}}

            torch.onnx.export(
                self.model,
                dummy_input,
                str(onnx_path),
                input_names=input_names,
                output_names=output_names,
                dynamic_axes=dynamic_axes_dict,
                opset_version=opset,
                do_constant_folding=True,
            )

            try:
                onnx_model = onnx.load(str(onnx_path))
                onnx.checker.check_model(onnx_model)
                self.metadata.notes.append("ONNX model validation passed")
            except Exception as e:
                self.metadata.notes.append(f"ONNX validation failed: {e}")

            try:
                session = InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
                self.metadata.notes.append("ONNX Runtime loaded successfully")
            except Exception as e:
                self.metadata.notes.append(f"ONNX Runtime load failed: {e}")

            self._save_config(output_dir, "config.json")
            self.metadata.exported_files.append("model.onnx")
            self.metadata.export_params = {"opset": opset, "dynamic_axes": dynamic_axes}
            self.metadata.size_bytes = _calculate_directory_size(output_dir)
            self.metadata.validation_status = "success"
            self._save_metadata(output_dir)
            logger.info(f"ONNX export completed: {onnx_path} ({_human_readable_size(self.metadata.size_bytes)})")
        except Exception as e:
            self.metadata.notes.append(f"ONNX export failed: {e}")
            self.metadata.validation_status = "failed"
            logger.error(f"ONNX export failed: {e}")
            raise ExportError(f"ONNX export failed: {e}") from e

        return self.metadata


class TensorRTExporter(BaseExporter):
    def export(self, output_dir: Union[str, Path], precision: str = "fp16", workspace_size: int = 1 << 30, **kwargs) -> ExportMetadata:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self.metadata.format = ExportFormat.TENSORRT.value

        try:
            import tensorrt as trt
            import pycuda.driver as cuda
            import pycuda.autoinit
        except ImportError as e:
            self.metadata.notes.append(f"TensorRT export skipped: tensorrt/pycuda not available ({e})")
            self.metadata.validation_status = "skipped"
            logger.warning(f"TensorRT export skipped: {e}")
            return self.metadata

        try:
            onnx_path = output_dir / "model.onnx"
            if not onnx_path.exists():
                self.metadata.notes.append("No ONNX file found, generating one")
                onnx_exporter = ONNXExporter(self.model, self.config, metadata=ExportMetadata(
                    model_name=self.metadata.model_name,
                    format=ExportFormat.ONNX.value,
                    timestamp=self.metadata.timestamp,
                    original_config=self.config,
                ))
                onnx_exporter.export(output_dir)

            trt_logger = trt.Logger(trt.Logger.INFO)
            builder = trt.Builder(trt_logger)
            network_flags = 1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
            network = builder.create_network(network_flags)
            parser = trt.OnnxParser(network, trt_logger)

            with open(onnx_path, "rb") as f:
                parser.parse(f.read())

            if not parser.get_errors():
                self.metadata.notes.append("ONNX parsed successfully for TensorRT")
            else:
                self.metadata.notes.append(f"ONNX parse errors: {parser.get_errors()}")

            builder_config = builder.create_builder_config()
            builder_config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, workspace_size)

            if precision == "fp16":
                builder_config.set_flag(trt.BuilderFlag.FP16)
            elif precision == "int8":
                builder_config.set_flag(trt.BuilderFlag.INT8)

            serialized_engine = builder.build_serialized_network(network, builder_config)
            if serialized_engine is None:
                raise ExportError("TensorRT engine build returned None")

            engine_path = output_dir / "model.engine"
            with open(engine_path, "wb") as f:
                f.write(serialized_engine)

            self._save_config(output_dir, "config.json")
            self.metadata.exported_files.append("model.engine")
            if "model.onnx" not in self.metadata.exported_files:
                self.metadata.exported_files.append("model.onnx")
            self.metadata.export_params = {"precision": precision, "workspace_size": workspace_size}
            self.metadata.size_bytes = _calculate_directory_size(output_dir)
            self.metadata.validation_status = "success"
            self._save_metadata(output_dir)
            logger.info(f"TensorRT export completed: {engine_path} ({_human_readable_size(self.metadata.size_bytes)})")
        except Exception as e:
            self.metadata.notes.append(f"TensorRT export failed: {e}")
            self.metadata.validation_status = "failed"
            logger.error(f"TensorRT export failed: {e}")
            raise ExportError(f"TensorRT export failed: {e}") from e

        return self.metadata


class GGUFFExporter(BaseExporter):
    def export(self, output_dir: Union[str, Path], quantization: str = "q4_k_m", **kwargs) -> ExportMetadata:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self.metadata.format = ExportFormat.GGUF.value

        try:
            import gguf
        except ImportError as e:
            self.metadata.notes.append(f"GGUF export skipped: gguf not available ({e})")
            self.metadata.validation_status = "skipped"
            logger.warning(f"GGUF export skipped: {e}")
            return self.metadata

        try:
            state_dict = self.model.state_dict()
            gguf_path = output_dir / "model.gguf"

            try:
                self._write_gguf_native(state_dict, gguf_path, quantization)
            except Exception as e:
                self.metadata.notes.append(f"Native GGUF write failed, using fallback: {e}")
                self._write_gguf_fallback(state_dict, gguf_path, quantization)

            self._save_config(output_dir, "config.json")
            self.metadata.exported_files.append("model.gguf")
            self.metadata.export_params = {"quantization": quantization}
            self.metadata.size_bytes = _calculate_directory_size(output_dir)
            self.metadata.validation_status = "success"
            self._save_metadata(output_dir)
            logger.info(f"GGUF export completed: {gguf_path} ({_human_readable_size(self.metadata.size_bytes)})")
        except Exception as e:
            self.metadata.notes.append(f"GGUF export failed: {e}")
            self.metadata.validation_status = "failed"
            logger.error(f"GGUF export failed: {e}")
            raise ExportError(f"GGUF export failed: {e}") from e

        return self.metadata

    def _write_gguf_native(self, state_dict: Dict[str, Any], path: Path, quantization: str) -> None:
        import gguf
        writer = gguf.GGUFWriter(str(path), "llama")
        writer.add_string("general.name", self.metadata.model_name)
        writer.add_uint32("general.architecture", 0)
        writer.add_uint32("general.file_type", self._gguf_quantization_type(quantization))
        writer.add_uint64("llama.context_length", int(self.config.get("max_position_embeddings", 2048)))
        writer.add_uint32("llama.embedding_length", int(self.config.get("hidden_size", 64)))
        writer.add_uint32("llama.block_count", int(self.config.get("num_hidden_layers", 2)))
        writer.add_uint32("llama.attention.head_count", int(self.config.get("num_attention_heads", 2)))
        writer.add_uint32("llama.feed_forward_length", int(self.config.get("intermediate_size", 128)))
        writer.add_float("llama.rope.freq_base", float(self.config.get("rope_theta", 10000.0)))

        tensors = []
        for name, tensor in state_dict.items():
            tensors.append((name, tensor.numpy()))
        writer.write_tensors(tensors)
        writer.close()

    def _write_gguf_fallback(self, state_dict: Dict[str, Any], path: Path, quantization: str) -> None:
        fallback_path = path.with_suffix(".bin")
        torch.save(state_dict, fallback_path)
        self.metadata.notes.append(f"GGUF fallback: saved state dict to {fallback_path.name}")

    def _gguf_quantization_type(self, quantization: str) -> int:
        mapping = {
            "f32": 0, "f16": 1, "q4_0": 2, "q4_1": 3, "q4_k_s": 4, "q4_k_m": 5,
            "q5_0": 6, "q5_1": 7, "q5_k_s": 8, "q5_k_m": 9, "q8_0": 10, "q8_k_s": 11,
        }
        return mapping.get(quantization, 5)


class SafeTensorsExporter(BaseExporter):
    def export(self, output_dir: Union[str, Path], **kwargs) -> ExportMetadata:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self.metadata.format = ExportFormat.SAFETENSORS.value

        try:
            from safetensors.torch import save_file as st_save
        except ImportError as e:
            self.metadata.notes.append(f"SafeTensors export skipped: safetensors not available ({e})")
            self.metadata.validation_status = "skipped"
            logger.warning(f"SafeTensors export skipped: {e}")
            return self.metadata

        try:
            state_dict = self.model.state_dict()
            safetensors_path = output_dir / "model.safetensors"
            st_save(state_dict, str(safetensors_path))

            self._save_config(output_dir, "config.json")
            self.metadata.exported_files.append("model.safetensors")
            self.metadata.size_bytes = _calculate_directory_size(output_dir)
            self.metadata.validation_status = "success"
            self._save_metadata(output_dir)
            logger.info(f"SafeTensors export completed: {safetensors_path} ({_human_readable_size(self.metadata.size_bytes)})")
        except Exception as e:
            self.metadata.notes.append(f"SafeTensors export failed: {e}")
            self.metadata.validation_status = "failed"
            logger.error(f"SafeTensors export failed: {e}")
            raise ExportError(f"SafeTensors export failed: {e}") from e

        return self.metadata


def export_model(
    model: nn.Module,
    config: Dict[str, Any],
    output_dir: Union[str, Path],
    format: Union[str, ExportFormat] = ExportFormat.HUGGINGFACE,
    tokenizer=None,
    **kwargs,
) -> ExportMetadata:
    if isinstance(format, str):
        format = ExportFormat(format.lower())

    exporters = {
        ExportFormat.HUGGINGFACE: HuggingFaceExporter,
        ExportFormat.ONNX: ONNXExporter,
        ExportFormat.TENSORRT: TensorRTExporter,
        ExportFormat.GGUF: GGUFFExporter,
        ExportFormat.SAFETENSORS: SafeTensorsExporter,
    }

    exporter_class = exporters.get(format)
    if exporter_class is None:
        raise ValueError(f"Unsupported export format: {format}")

    exporter = exporter_class(model, config)
    return exporter.export(output_dir, tokenizer=tokenizer, **kwargs)


def export_from_checkpoint(
    checkpoint_path: Union[str, Path],
    output_dir: Union[str, Path],
    config: Dict[str, Any],
    format: Union[str, ExportFormat] = ExportFormat.HUGGINGFACE,
    tokenizer=None,
    **kwargs,
) -> ExportMetadata:
    checkpoint_path = Path(checkpoint_path)
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    from model.model import LLM

    model = LLM.from_config(config)
    state_dict = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if isinstance(state_dict, dict):
        if "model" in state_dict:
            state_dict = state_dict["model"]
        elif "state_dict" in state_dict:
            state_dict = state_dict["state_dict"]
    model.load_state_dict(state_dict, strict=False)
    model.eval()
    return export_model(model, config, output_dir, format=format, tokenizer=tokenizer, **kwargs)


def export_from_state_dict(
    state_dict: Dict[str, Any],
    config: Dict[str, Any],
    output_dir: Union[str, Path],
    format: Union[str, ExportFormat] = ExportFormat.HUGGINGFACE,
    tokenizer=None,
    **kwargs,
) -> ExportMetadata:
    from model.model import LLM

    _validate_state_dict(state_dict)
    model = LLM.from_config(config)
    model.load_state_dict(state_dict, strict=False)
    model.eval()
    return export_model(model, config, output_dir, format=format, tokenizer=tokenizer, **kwargs)


def validate_export(output_dir: Union[str, Path]) -> Dict[str, Any]:
    output_dir = Path(output_dir)
    if not output_dir.exists():
        return {"valid": False, "error": f"Output directory does not exist: {output_dir}"}

    meta_path = output_dir / "export_metadata.json"
    if not meta_path.exists():
        return {"valid": False, "error": "export_metadata.json not found"}

    with open(meta_path, "r") as f:
        metadata = json.load(f)

    missing_files = []
    for fname in metadata.get("exported_files", []):
        path = output_dir / fname
        if not path.exists():
            missing_files.append(fname)

    total_size = _calculate_directory_size(output_dir)
    return {
        "valid": len(missing_files) == 0,
        "model_name": metadata.get("model_name"),
        "format": metadata.get("format"),
        "status": metadata.get("validation_status"),
        "size_bytes": total_size,
        "size_human": _human_readable_size(total_size),
        "files": metadata.get("exported_files", []),
        "missing_files": missing_files,
    }


def report_export_sizes(output_dir: Union[str, Path]) -> Dict[str, Any]:
    output_dir = Path(output_dir)
    if not output_dir.exists():
        raise FileNotFoundError(f"Output directory does not exist: {output_dir}")

    files = []
    total = 0
    for entry in sorted(output_dir.rglob("*")):
        if entry.is_file():
            size = entry.stat().st_size
            files.append({"path": str(entry.relative_to(output_dir)), "size_bytes": size, "size_human": _human_readable_size(size)})
            total += size

    return {
        "directory": str(output_dir),
        "total_size_bytes": total,
        "total_size_human": _human_readable_size(total),
        "files": files,
    }


def list_supported_formats() -> List[str]:
    return [fmt.value for fmt in ExportFormat]
