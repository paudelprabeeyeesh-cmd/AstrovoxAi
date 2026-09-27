#!/usr/bin/env python3
"""
Start the AstrovoxAI inference API server.

Usage:
    python examples/serve_api.py --config configs/config_4b.yaml --checkpoint model.pt --port 8000
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.llm.inference.engine import run_server


def main():
    parser = argparse.ArgumentParser(description="Start inference API server")
    parser.add_argument("--config", default=None, help="Path to model config YAML")
    parser.add_argument("--checkpoint", default=None, help="Path to model checkpoint")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--device", default=None)
    args = parser.parse_args()

    print(f"Starting inference server on {args.host}:{args.port}")
    run_server(
        host=args.host,
        port=args.port,
        config_path=args.config,
        checkpoint_path=args.checkpoint,
        device=args.device,
    )


if __name__ == "__main__":
    main()
