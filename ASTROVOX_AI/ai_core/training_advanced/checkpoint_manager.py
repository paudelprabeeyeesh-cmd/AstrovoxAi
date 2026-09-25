from typing import Optional, Dict, Any, List
import os
import torch
import torch.nn as nn
from datetime import datetime


class CheckpointManager:
    def __init__(self, checkpoint_dir: str = './checkpoints', max_to_keep: int = 5, save_interval: int = 1000):
        self.checkpoint_dir = checkpoint_dir
        self.max_to_keep = max_to_keep
        self.save_interval = save_interval
        os.makedirs(checkpoint_dir, exist_ok=True)
        self.checkpoints: List[str] = []

    def save(self, model: nn.Module, optimizer: torch.optim.Optimizer, epoch: int, step: int, metrics: Optional[Dict[str, float]] = None) -> str:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'checkpoint_epoch{epoch}_step{step}_{timestamp}.pt'
        path = os.path.join(self.checkpoint_dir, filename)
        state = {'model': model.state_dict(), 'optimizer': optimizer.state_dict(), 'epoch': epoch, 'step': step}
        if metrics:
            state['metrics'] = metrics
        torch.save(state, path)
        self.checkpoints.append(path)
        if len(self.checkpoints) > self.max_to_keep:
            old = self.checkpoints.pop(0)
            if os.path.exists(old):
                os.remove(old)
        return path

    def load(self, path: str, model: nn.Module, optimizer: Optional[torch.optim.Optimizer] = None) -> Dict[str, Any]:
        state = torch.load(path, map_location='cpu')
        model.load_state_dict(state['model'])
        if optimizer and 'optimizer' in state:
            optimizer.load_state_dict(state['optimizer'])
        return state

    def get_latest(self) -> Optional[str]:
        if self.checkpoints:
            return self.checkpoints[-1]
        return None
