#!/usr/bin/env python3
"""
Export a model to different formats.

Usage:
    python examples/export_model.py --checkpoint model.pt --config configs/config_4b.yaml --format huggingface --output-dir export/hf
    python examples/export_model.py --checkpoint model.pt --config configs/config_4b.yaml --format onnx --output-dir export/onnx
    python examples/export_model.py --checkpoint model.pt --config configs/config_4b.yaml --format gguf --output-dir export/gguf
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
from models.llm.model.model import LLM
from models.llm.export import export_from_checkpoint, list_supported_formats, ExportFormat


def main():
    parser = argparse.ArgumentParser(description="Export model to different formats")
    parser.add_argument("--checkpoint", required=True, help="Path to model checkpoint")
    parser.add_argument("--config", required=True, help="Path to model config YAML")
    parser.add_argument("--format", default="huggingface", choices=list_supported_formats())
    parser.add_argument("--output-dir", required=True, help="Output directory")
    args = parser.parse_args()

    if not os.path.exists(args.checkpoint):
        raise FileNotFoundError(f"Checkpoint not found: {args.checkpoint}")

    fmt = ExportFormat(args.format)
    print(f"Exporting {args.checkpoint} to {fmt.value} -> {args.output_dir}")

    metadata = export_from_checkpoint(
        checkpoint_path=args.checkpoint,
        output_dir=args.output_dir,
        config={},
        format=fmt,
    )

    print(f"Format: {metadata.format}")
    print(f"Status: {metadata.validation_status}")
    print(f"Files: {metadata.exported_files}")
    print(f"Size: {metadata.size_bytes / (1024**3):.2f} GB" if metadata.size_bytes > 1024**3 else f"Size: {metadata.size_bytes / (1024**2):.2f} MB")
    if metadata.notes:
        print("Notes:")
        for note in metadata.notes:
            print(f"  - {note}")


if __name__ == "__main__":
    main()
