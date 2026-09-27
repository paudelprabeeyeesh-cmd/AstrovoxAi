import torch
import os
from ..model.model import LLM
from ..tokenizer.train_tokenizer import load_tokenizer
from ..utils.helpers import load_config, get_device, set_cpu_threads


def generate(model, tokenizer, prompt, max_new_tokens=100, temperature=1.0, top_k=None, device="cpu"):
    model.eval()
    input_ids = torch.tensor(tokenizer.encode(prompt).ids, dtype=torch.long).unsqueeze(0).to(device)
    for _ in range(max_new_tokens):
        with torch.no_grad():
            outputs = model(input_ids)
            logits = outputs["logits"][:, -1, :] / temperature
            if top_k is not None:
                v, _ = torch.topk(logits, top_k)
                logits[logits < v[:, [-1]]] = float("-inf")
            probs = torch.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            input_ids = torch.cat([input_ids, next_token], dim=1)
            if next_token.item() == tokenizer.token_to_id("<eos>"):
                break
    return tokenizer.decode(input_ids[0].tolist())


def main(config_path="configs/config_4b.yaml", checkpoint_path="model.pt", prompt="Hello"):
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
        mem = LLM.estimate_memory_from_config(config, dtype_bytes=2 if dtype in (torch.float16, torch.bfloat16) else 4)

    model = LLM(config, device=torch.device(device), dtype=dtype)
    if os.path.exists(checkpoint_path):
        model.load_state_dict(torch.load(checkpoint_path, map_location=device, weights_only=True))
    tokenizer = load_tokenizer(config.get("tokenizer_path", "tokenizer.json"))
    print(generate(model, tokenizer, prompt, device=device))


if __name__ == "__main__":
    main()
