import os
import time
import torch
from ..utils.helpers import load_config


def save_checkpoint(model, optimizer, scheduler, epoch, best_val_loss, path, config=None, global_step=None):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    ckpt = {
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict() if scheduler is not None else None,
        "best_val_loss": best_val_loss,
        "timestamp": time.time(),
        "config": config,
        "global_step": global_step,
    }
    torch.save(ckpt, path)


def load_checkpoint(model, optimizer, scheduler, path, device="cpu"):
    ckpt = torch.load(path, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    if optimizer is not None and ckpt.get("optimizer_state_dict"):
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
    if scheduler is not None and ckpt.get("scheduler_state_dict"):
        scheduler.load_state_dict(ckpt["scheduler_state_dict"])
    return ckpt.get("epoch", 0), ckpt.get("best_val_loss", float("inf"))


def list_checkpoints(dir_path):
    if not os.path.isdir(dir_path):
        return []
    ckpts = []
    for f in os.listdir(dir_path):
        if f.endswith(".pt"):
            path = os.path.join(dir_path, f)
            ckpts.append(path)
    return sorted(ckpts, key=lambda p: os.path.getmtime(p))


def remove_old_checkpoints(dir_path, keep_last_n=3):
    ckpts = list_checkpoints(dir_path)
    for old in ckpts[:-keep_last_n]:
        if os.path.exists(old):
            os.remove(old)


def get_latest_checkpoint(dir_path):
    ckpts = list_checkpoints(dir_path)
    return ckpts[-1] if ckpts else None
