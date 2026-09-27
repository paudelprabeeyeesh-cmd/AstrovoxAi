import os
import sys
import torch

from ..model.model import LLM
from ..tokenizer.train_tokenizer import load_tokenizer
from ..utils.helpers import load_config, get_device
from .generate import generate


def chat_loop(model, tokenizer, device="cpu"):
    print("Chat ready. Type 'quit' to exit.")
    while True:
        prompt = input("You: ")
        if prompt.lower() in ("quit", "exit"):
            break
        response = generate(model, tokenizer, f"You: {prompt}\nAI:", max_new_tokens=200, device=device)
        print(response)


def main(config_path=None, checkpoint_path=None):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    llm_root = os.path.abspath(os.path.join(base_dir, ".."))

    if config_path is None:
        config_path = os.path.join(llm_root, "configs", "config_4b.yaml")
    if checkpoint_path is None:
        checkpoint_path = os.path.join(llm_root, "model.pt")

    config = load_config(config_path)
    device = get_device()
    if device == "cpu":
        set_cpu_threads(min(4, os.cpu_count() or 2))

    dtype = torch.bfloat16 if config.get("mixed_precision") == "bf16" and device != "cuda" else torch.float32
    if device == "cuda" and config.get("mixed_precision") == "fp16":
        dtype = torch.float16

    mem = LLM.estimate_memory_from_config(config, dtype_bytes=2 if dtype in (torch.float16, torch.bfloat16) else 4)
    if device == "cpu" and mem.get("total_base_gb", 0) > 8:
        print(f"Warning: model needs ~{mem['total_base_gb']:.1f}GB; reducing precision")
        dtype = torch.bfloat16 if hasattr(torch, 'bfloat16') else torch.float32

    model = LLM(config, device=torch.device(device), dtype=dtype)
    if os.path.exists(checkpoint_path):
        model.load_state_dict(torch.load(checkpoint_path, map_location=device, weights_only=True))
    tokenizer = load_tokenizer(config.get("tokenizer_path", os.path.join(llm_root, "tokenizer.json")))
    chat_loop(model, tokenizer, device)


if __name__ == "__main__":
    main()
