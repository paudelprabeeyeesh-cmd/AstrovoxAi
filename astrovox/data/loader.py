"""Dataset and loader abstractions for training.

The design is deliberately small: a dataset yields samples, a sampler decides
in what order, and a loader assembles batches. Keeping those three separate is
what makes shuffling, distributed sampling, and prefetching composable rather
than special cases inside a loader.
"""

from __future__ import annotations

import queue
import threading
from typing import Any, Callable, Iterator, Sequence

import numpy as np

from astrovox.tensor.tensor import Tensor


class Dataset:
    """A map-style dataset backed by an in-memory sequence.

    Subclasses implement :meth:`__getitem__` and :meth:`__len__`; this base
    covers the common case where the samples already live in a list.
    """

    def __init__(self, samples: Sequence[Any] | None = None) -> None:
        self.samples: list[Any] = list(samples or [])

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> Any:
        return self.samples[index]

    def __iter__(self) -> Iterator[Any]:
        for index in range(len(self)):
            yield self[index]

    @property
    def feature_shape(self) -> tuple[int, ...]:
        """Shape of one sample's features, discovered from the first sample."""
        if not len(self):
            return ()
        sample = self[0]
        target = sample[0] if isinstance(sample, (tuple, list)) else sample
        shape = getattr(target, "shape", None)
        return tuple(shape.dims) if shape is not None else (len(target),)

    @property
    def label_shape(self) -> tuple[int, ...]:
        """Shape of one sample's label, or an empty shape for scalars."""
        if not len(self):
            return ()
        sample = self[0]
        if not isinstance(sample, (tuple, list)) or len(sample) < 2:
            return ()
        shape = getattr(sample[1], "shape", None)
        return tuple(shape.dims) if shape is not None else ()

    def subset(self, count: int) -> "Dataset":
        """Return a dataset holding the first ``count`` samples."""
        clone = type(self)()
        clone.samples = self.samples[:count]
        return clone

    def shuffle(self, seed: int = 0) -> "Dataset":
        """Return a dataset with the samples in a seeded random order."""
        rng = np.random.default_rng(seed)
        order = rng.permutation(len(self))
        clone = type(self)()
        clone.samples = [self.samples[i] for i in order]
        return clone


class IterableDataset:
    """Base class for datasets that stream rather than index."""

    def __iter__(self) -> Iterator[Any]:  # pragma: no cover - interface
        raise NotImplementedError


class TensorDataset(Dataset):
    """A dataset over aligned feature and label tensors."""

    def __init__(self, features: Any, labels: Any) -> None:
        super().__init__()
        self.features = features
        self.labels = labels

    def __len__(self) -> int:
        shape = getattr(self.features, "shape", None)
        return int(shape.dims[0]) if shape is not None else len(self.features)

    def __getitem__(self, index: int) -> tuple[Tensor, Tensor]:
        return self.features[index], self.labels[index]


# ----------------------------------------------------------------------
# Samplers
# ----------------------------------------------------------------------


class SequentialSampler:
    """Yields indices in order."""

    def __init__(self, count: int, start: int = 0) -> None:
        self.count = count
        self.start = start

    def __iter__(self) -> Iterator[int]:
        return iter(range(self.start, self.count))

    def __len__(self) -> int:
        return max(0, self.count - self.start)


class RandomSampler:
    """Yields indices in a seeded random order, with or without replacement."""

    def __init__(self, count: int, seed: int = 0, replacement: bool = False) -> None:
        self.count = count
        self.seed = seed
        self.replacement = replacement

    def __iter__(self) -> Iterator[int]:
        if self.count == 0:
            return iter(())
        rng = np.random.default_rng(self.seed)
        if self.replacement:
            return (int(rng.integers(0, self.count)) for _ in range(self.count))
        return (int(i) for i in rng.permutation(self.count))

    def __len__(self) -> int:
        return self.count


class DistributedSampler:
    """Splits indices across ranks so each worker sees a disjoint shard.

    Every rank pads to the same length, which keeps a step's batch shape
    identical everywhere and therefore keeps collective operations aligned.
    """

    def __init__(
        self, count: int, num_replicas: int = 1, rank: int = 0, seed: int = 0, shuffle: bool = True
    ) -> None:
        if num_replicas < 1:
            raise ValueError(f"num_replicas must be at least 1, got {num_replicas}")
        if not 0 <= rank < num_replicas:
            raise ValueError(f"rank {rank} is out of range for {num_replicas} replicas")
        self.count = count
        self.num_replicas = num_replicas
        self.rank = rank
        self.seed = seed
        self.shuffle = shuffle
        self.epoch = 0

    def set_epoch(self, epoch: int) -> None:
        """Change the shuffle order, as every epoch should differ."""
        self.epoch = epoch

    def __iter__(self) -> Iterator[int]:
        if self.count == 0:
            return iter(())
        order = np.arange(self.count)
        if self.shuffle:
            rng = np.random.default_rng(self.seed + self.epoch)
            order = rng.permutation(self.count)
        remainder = self.count % self.num_replicas
        if remainder:
            # Pad so every rank gets the same number of samples. The padded
            # entries repeat real indices, which is intentional: it keeps the
            # batch shape identical on every rank. They must not be wrapped
            # back into range, or two ranks would train on the same sample.
            needed = self.num_replicas - remainder
            order = np.concatenate([order, np.resize(order, needed)])
        return iter(int(i) for i in order[self.rank :: self.num_replicas])

    def __len__(self) -> int:
        if self.count == 0:
            return 0
        return (self.count + self.num_replicas - 1) // self.num_replicas


class BatchSampler:
    """Groups indices from a sampler into batches of a fixed size."""

    def __init__(self, sampler: Any, batch_size: int, drop_last: bool = False) -> None:
        if batch_size < 1:
            raise ValueError(f"batch_size must be at least 1, got {batch_size}")
        self.sampler = sampler
        self.batch_size = batch_size
        self.drop_last = drop_last

    def __iter__(self) -> Iterator[list[int]]:
        batch: list[int] = []
        for index in self.sampler:
            batch.append(index)
            if len(batch) == self.batch_size:
                yield batch
                batch = []
        if batch and not self.drop_last:
            yield batch

    def __len__(self) -> int:
        total = len(self.sampler)
        if self.drop_last:
            return total // self.batch_size
        return (total + self.batch_size - 1) // self.batch_size


# ----------------------------------------------------------------------
# Collation and loading
# ----------------------------------------------------------------------


def default_collate(samples: Sequence[Any]) -> Any:
    """Combine a list of samples into a batch.

    Tensors stack along a new leading axis. A tuple of tensors becomes a tuple
    of batched tensors, which is the shape a training loop expects. Anything
    else becomes a list, so a heterogeneous dataset still loads.
    """
    if not samples:
        return []
    first = samples[0]
    if isinstance(first, Tensor):
        return Tensor.from_numpy(
            np.stack([s.numpy() for s in samples]), first.dtype, first.device
        )
    if isinstance(first, tuple):
        width = max(len(s) for s in samples)
        columns = []
        for position in range(width):
            column = [s[position] if len(s) > position else None for s in samples]
            columns.append(
                default_collate(column)
                if column and all(isinstance(c, Tensor) for c in column)
                else column
            )
        return tuple(columns)
    return list(samples)


class DataLoader:
    """Assembles batches from a dataset.

    Args:
        dataset: the dataset to read.
        batch_size: samples per batch.
        shuffle: draw indices in random order.
        drop_last: discard a trailing partial batch.
        num_workers: threads used to prefetch batches.
        seed: seed for the sampler.
        sampler: an explicit sampler, overriding ``shuffle``.
        collate_fn: how to combine samples into a batch.
        prefetch_factor: batches to queue ahead per worker.
    """

    def __init__(
        self,
        dataset: Any,
        batch_size: int = 1,
        shuffle: bool = False,
        drop_last: bool = False,
        num_workers: int = 0,
        seed: int = 0,
        sampler: Any = None,
        collate_fn: Callable[[Sequence[Any]], Any] = default_collate,
        prefetch_factor: int = 2,
    ) -> None:
        if batch_size < 1:
            raise ValueError(f"batch_size must be at least 1, got {batch_size}")
        if num_workers < 0:
            raise ValueError(f"num_workers cannot be negative, got {num_workers}")
        self.dataset = dataset
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.drop_last = drop_last
        self.num_workers = num_workers
        self.seed = seed
        self.collate_fn = collate_fn
        self.prefetch_factor = max(1, prefetch_factor)
        self._sampler = sampler
        self.epoch = 0

    def _build_sampler(self) -> Any:
        """Return the sampler for the current epoch."""
        if self._sampler is not None:
            return self._sampler
        if self.shuffle:
            return RandomSampler(len(self.dataset), seed=self.seed + self.epoch)
        return SequentialSampler(len(self.dataset))

    def set_epoch(self, epoch: int) -> None:
        """Advance the epoch, which changes the shuffle order."""
        self.epoch = epoch
        if hasattr(self._sampler, "set_epoch"):
            self._sampler.set_epoch(epoch)

    def __len__(self) -> int:
        """Return the number of batches in one epoch."""
        total = len(self._build_sampler())
        if self.drop_last:
            return total // self.batch_size
        return (total + self.batch_size - 1) // self.batch_size

    def _materialize(self, indices: Sequence[int]) -> Any:
        """Fetch and collate the samples for one batch of indices."""
        return self.collate_fn([self.dataset[i] for i in indices])

    def __iter__(self) -> Iterator[Any]:
        """Yield batches for one epoch."""
        indices = list(self._build_sampler())
        batches = [
            indices[start : start + self.batch_size]
            for start in range(0, len(indices), self.batch_size)
        ]
        if self.drop_last:
            batches = [b for b in batches if len(b) == self.batch_size]
        if not batches:
            return

        if self.num_workers <= 0:
            for chunk in batches:
                yield self._materialize(chunk)
            return

        # Prefetch on a background thread so the next batch is assembled while
        # the caller is still working through the current one. One producer is
        # deliberate: several producers would each walk the whole batch list
        # and duplicate every batch, and the work here is cheap next to the
        # model's own compute.
        pending: "queue.Queue[Any]" = queue.Queue(maxsize=self.prefetch_factor)
        stop = threading.Event()
        failures: list[BaseException] = []

        def produce() -> None:
            try:
                for chunk in batches:
                    if stop.is_set():
                        break
                    pending.put(self._materialize(chunk))
            except BaseException as exc:
                failures.append(exc)
            finally:
                pending.put(None)

        worker = threading.Thread(target=produce, daemon=True)
        worker.start()
        try:
            while True:
                item = pending.get()
                if item is None:
                    break
                yield item
        finally:
            stop.set()
            worker.join(timeout=5.0)
        if failures:
            raise failures[0]


def infinite_loader(loader: DataLoader) -> Iterator[Any]:
    """Yield batches forever, restarting each epoch.

    Training runs for a configured number of steps, which is usually more than
    one epoch of batches, so the stream has to repeat.
    """
    from itertools import islice

    epoch = 0
    while True:
        loader.set_epoch(epoch)
        produced = False
        for batch in loader:
            produced = True
            yield batch
        if not produced:
            return
        epoch += 1


def tensor_dataset(features: Any, labels: Any) -> TensorDataset:
    """Build a dataset from aligned feature and label tensors."""
    return TensorDataset(features, labels)


__all__ = [
    "BatchSampler",
    "DataLoader",
    "Dataset",
    "DistributedSampler",
    "IterableDataset",
    "RandomSampler",
    "SequentialSampler",
    "TensorDataset",
    "default_collate",
    "infinite_loader",
    "tensor_dataset",
]
