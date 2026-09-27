import os
import yaml


def load_config(config_path="configs/config_100m.yaml"):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def save_config(config, config_path):
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def get_device():
    import torch
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    else:
        return "cpu"
