import os
import yaml
import torch


def load_config(config_path="configs/config_100m.yaml"):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def save_config(config, config_path):
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def count_parameters(model):
    try:
        return sum(p.numel() for p in model.parameters() if p.requires_grad)
    except Exception:
        return 0


def get_device():
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    else:
        return "cpu"


def set_cpu_threads(workers: int = 2):
    if torch.get_num_threads() > workers:
        torch.set_num_threads(workers)


class ValidationSplit:
    def __init__(self, dataset, val_ratio: float = 0.05, seed: int = 42):
        self.dataset = dataset
        n = len(dataset)
        g = torch.Generator().manual_seed(seed)
        indices = torch.randperm(n, generator=g).tolist()
        split = int(n * (1 - val_ratio))
        self.train_idx = indices[:split]
        self.val_idx = indices[split:]

    def train_dataset(self):
        from torch.utils.data import Subset
        return Subset(self.dataset, self.train_idx)

    def val_dataset(self):
        from torch.utils.data import Subset
        return Subset(self.dataset, self.val_idx)
