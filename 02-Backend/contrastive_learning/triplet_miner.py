import numpy as np
from typing import Dict, List, Tuple


class TripletMiner:
    def __init__(self, margin: float = 0.2):
        if margin <= 0:
            raise ValueError("margin must be positive")
        self.margin = float(margin)

    def _pairwise_distances(self, embeddings: np.ndarray) -> np.ndarray:
        sq_norms = np.sum(embeddings ** 2, axis=1)
        dists = sq_norms[:, None] + sq_norms[None, :] - 2.0 * (embeddings @ embeddings.T)
        dists = np.maximum(dists, 0.0)
        return np.sqrt(dists + 1e-12)

    def mine_random(self, embeddings: np.ndarray, labels: np.ndarray, num_triplets: int = 32) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        n = len(embeddings)
        anchors: List[int] = []
        positives: List[int] = []
        negatives: List[int] = []

        for _ in range(num_triplets):
            anchor_idx = np.random.randint(0, n)
            anchor_label = labels[anchor_idx]

            pos_candidates = np.where(labels == anchor_label)[0]
            pos_candidates = pos_candidates[pos_candidates != anchor_idx]

            neg_candidates = np.where(labels != anchor_label)[0]

            if len(pos_candidates) == 0 or len(neg_candidates) == 0:
                continue

            pos_idx = int(np.random.choice(pos_candidates))
            neg_idx = int(np.random.choice(neg_candidates))

            anchors.append(anchor_idx)
            positives.append(pos_idx)
            negatives.append(neg_idx)

        if not anchors:
            empty = np.empty((0,), dtype=np.int64)
            return empty, empty, empty

        return np.array(anchors, dtype=np.int64), np.array(positives, dtype=np.int64), np.array(negatives, dtype=np.int64)

    def mine_hard(self, embeddings: np.ndarray, labels: np.ndarray, num_triplets: int = 32) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        dists = self._pairwise_distances(embeddings)
        n = len(embeddings)
        anchors: List[int] = []
        positives: List[int] = []
        negatives: List[int] = []

        attempts = 0
        max_attempts = num_triplets * 10

        while len(anchors) < num_triplets and attempts < max_attempts:
            anchor_idx = np.random.randint(0, n)
            anchor_label = labels[anchor_idx]

            pos_candidates = np.where(labels == anchor_label)[0]
            neg_candidates = np.where(labels != anchor_label)[0]

            if len(pos_candidates) == 0 or len(neg_candidates) == 0:
                attempts += 1
                continue

            pos_dists = dists[anchor_idx, pos_candidates]
            hard_pos_idx = int(pos_candidates[np.argmax(pos_dists)])

            neg_dists = dists[anchor_idx, neg_candidates]
            hard_neg_idx = int(neg_candidates[np.argmin(neg_dists)])

            anchors.append(anchor_idx)
            positives.append(hard_pos_idx)
            negatives.append(hard_neg_idx)
            attempts += 1

        if not anchors:
            empty = np.empty((0,), dtype=np.int64)
            return {
                "anchors": empty,
                "positives": empty,
                "negatives": empty,
            }

        return {
            "anchors": np.array(anchors, dtype=np.int64),
            "positives": np.array(positives, dtype=np.int64),
            "negatives": np.array(negatives, dtype=np.int64),
        }

    def mine_semi_hard(self, embeddings: np.ndarray, labels: np.ndarray, num_triplets: int = 32) -> Dict[str, np.ndarray]:
        dists = self._pairwise_distances(embeddings)
        n = len(embeddings)
        anchors: List[int] = []
        positives: List[int] = []
        negatives: List[int] = []

        attempts = 0
        max_attempts = num_triplets * 10

        while len(anchors) < num_triplets and attempts < max_attempts:
            anchor_idx = np.random.randint(0, n)
            anchor_label = labels[anchor_idx]

            pos_candidates = np.where(labels == anchor_label)[0]
            neg_candidates = np.where(labels != anchor_label)[0]

            if len(pos_candidates) == 0 or len(neg_candidates) == 0:
                attempts += 1
                continue

            pos_dists = dists[anchor_idx, pos_candidates]
            pos_idx = int(pos_candidates[np.argmax(pos_dists)])

            neg_dists = dists[anchor_idx, neg_candidates]
            semi_hard_negatives = neg_candidates[neg_dists > pos_dists.max()]

            if len(semi_hard_negatives) == 0:
                attempts += 1
                continue

            neg_idx = int(np.random.choice(semi_hard_negatives))

            anchors.append(anchor_idx)
            positives.append(pos_idx)
            negatives.append(neg_idx)
            attempts += 1

        if not anchors:
            empty = np.empty((0,), dtype=np.int64)
            return {
                "anchors": empty,
                "positives": empty,
                "negatives": empty,
            }

        return {
            "anchors": np.array(anchors, dtype=np.int64),
            "positives": np.array(positives, dtype=np.int64),
            "negatives": np.array(negatives, dtype=np.int64),
        }

    def mine(self, embeddings: np.ndarray, labels: np.ndarray, strategy: str = "random", num_triplets: int = 32) -> Dict[str, np.ndarray]:
        strategy = strategy.lower()
        if strategy == "random":
            a, p, n = self.mine_random(embeddings, labels, num_triplets)
        elif strategy == "hard":
            result = self.mine_hard(embeddings, labels, num_triplets)
            a, p, n = result["anchors"], result["positives"], result["negatives"]
        elif strategy == "semi_hard":
            result = self.mine_semi_hard(embeddings, labels, num_triplets)
            a, p, n = result["anchors"], result["positives"], result["negatives"]
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        return {
            "anchors": a,
            "positives": p,
            "negatives": n,
        }

    def compute_triplet_loss(self, embeddings: np.ndarray, anchors: np.ndarray, positives: np.ndarray, negatives: np.ndarray) -> float:
        if len(anchors) == 0:
            return 0.0

        a = embeddings[anchors]
        p = embeddings[positives]
        n = embeddings[negatives]

        pos_dist = np.sum((a - p) ** 2, axis=1)
        neg_dist = np.sum((a - n) ** 2, axis=1)

        loss = float(np.mean(np.maximum(self.margin + pos_dist - neg_dist, 0.0)))
        return loss
