import torch
from model.model import LLM
from tokenizer.train_tokenizer import load_tokenizer
from utils.helpers import load_config, get_device


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


def main(config_path="configs/config_100m.yaml", checkpoint_path="model.pt", prompt="Hello"):
    config = load_config(config_path)
    device = get_device()
    model = LLM(config).to(device)
    if os.path.exists(checkpoint_path):
        model.load_state_dict(torch.load(checkpoint_path, map_location=device, weights_only=True))
    tokenizer = load_tokenizer(config.get("tokenizer_path", "tokenizer.json"))
    print(generate(model, tokenizer, prompt, device=device))


if __name__ == "__main__":
    import os
    main()
