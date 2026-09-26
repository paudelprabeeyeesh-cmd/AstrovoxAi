from typing import Dict, Any, List
import json
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np


class MemoryVisualization:
    @staticmethod
    def plot_importance_over_time(memories: List[Dict[str, Any]], title: str = 'Memory Importance Over Time') -> str:
        if not memories:
            return 'No memories to visualize'
        timestamps = [datetime.fromisoformat(m.get('last_accessed', datetime.now().isoformat())) for m in memories]
        importances = [m.get('importance', 0.5) for m in memories]
        plt.figure(figsize=(10, 5))
        plt.plot(timestamps, importances, marker='o', linestyle='-', markersize=3)
        plt.title(title)
        plt.xlabel('Time')
        plt.ylabel('Importance')
        plt.grid(True, alpha=0.3)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.tight_layout()
        path = 'memory_importance.png'
        plt.savefig(path)
        plt.close()
        return path

    @staticmethod
    def plot_memory_heatmap(memories: List[Dict[str, Any]], title: str = 'Memory Heatmap') -> str:
        if not memories:
            return 'No memories to visualize'
        scores = np.array([m.get('combined_score', 0.5) for m in memories]).reshape(-1, 1)
        plt.figure(figsize=(6, max(4, len(memories) * 0.2)))
        plt.imshow(scores.T, aspect='auto', cmap='YlOrRd')
        plt.colorbar(label='Score')
        plt.title(title)
        plt.yticks([])
        plt.tight_layout()
        path = 'memory_heatmap.png'
        plt.savefig(path)
        plt.close()
        return path

    @staticmethod
    def plot_memory_distribution(memories: List[Dict[str, Any]], title: str = 'Memory Distribution') -> str:
        categories: Dict[str, int] = {}
        for mem in memories:
            cat = mem.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1
        labels = list(categories.keys())
        sizes = list(categories.values())
        plt.figure(figsize=(8, 8))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        plt.title(title)
        plt.tight_layout()
        path = 'memory_distribution.png'
        plt.savefig(path)
        plt.close()
        return path

    @staticmethod
    def export_json(memories: List[Dict[str, Any]], path: str) -> None:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'memories': memories, 'generated_at': datetime.now().isoformat()}, f, indent=2)
