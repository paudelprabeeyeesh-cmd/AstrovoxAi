import os

import torch


def save_checkpoint(model, optimizer, scheduler, step, checkpoint_dir, prefix="checkpoint"):
    os.makedirs(checkpoint_dir, exist_ok=True)
    state = {
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict() if optimizer is not None else None,
        "scheduler": scheduler.state_dict() if scheduler is not None else None,
        "step": step,
    }
    path = os.path.join(checkpoint_dir, f"{prefix}_{step}.pt")
    torch.save(state, path)
    print(f"Checkpoint saved to {path}")


def load_checkpoint(model, optimizer, scheduler, checkpoint_dir, step=None, prefix="checkpoint"):
    if step is not None:
        path = os.path.join(checkpoint_dir, f"{prefix}_{step}.pt")
    else:
        checkpoints = sorted([f for f in os.listdir(checkpoint_dir) if f.startswith(prefix)])
        if not checkpoints:
            return 0
        path = os.path.join(checkpoint_dir, checkpoints[-1])
    state = torch.load(path, map_location="cpu")
    model.load_state_dict(state["model"])
    if optimizer is not None and state["optimizer"] is not None:
        optimizer.load_state_dict(state["optimizer"])
    if scheduler is not None and state["scheduler"] is not None:
        scheduler.load_state_dict(state["scheduler"])
    print(f"Loaded checkpoint from {path}")
    return state.get("step", 0)
