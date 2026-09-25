from typing import Optional, List, Dict, Any
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, Subset


class CurriculumLearning:
    def __init__(self, dataset: Dataset, difficulty_fn: callable, start_ratio: float = 0.2, end_ratio: float = 1.0, epochs: int = 10):
        self.dataset = dataset
        self.difficulty_fn = difficulty_fn
        self.start_ratio = start_ratio
        self.end_ratio = end_ratio
        self.epochs = epochs
        self.current_epoch = 0
        self.difficulties: List[float] = []

    def compute_difficulties(self) -> List[float]:
        self.difficulties = []
        for i in range(len(self.dataset)):
            sample = self.dataset[i]
            difficulty = self.difficulty_fn(sample)
            self.difficulties.append(difficulty)
        return self.difficulties

    def get_schedule(self) -> List[Subset]:
        if not self.difficulties:
            self.compute_difficulties()
        sorted_indices = sorted(range(len(self.difficulties)), key=lambda i: self.difficulties[i])
        subsets = []
        for epoch in range(self.epochs):
            ratio = self.start_ratio + (self.end_ratio - self.start_ratio) * (epoch / max(self.epochs - 1, 1))
            num_samples = int(len(sorted_indices) * ratio)
            subset = Subset(self.dataset, sorted_indices[:num_samples])
            subsets.append(subset)
        return subsets

    def step(self, epoch: int) -> DataLoader:
        self.current_epoch = epoch
        schedule = self.get_schedule()
        loader = DataLoader(schedule[epoch], batch_size=32, shuffle=True, num_workers=4)
        return loader
