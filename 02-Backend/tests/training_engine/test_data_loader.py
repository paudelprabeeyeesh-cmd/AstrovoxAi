import json
import os

from training_engine.data_loader import DataLoader


def test_len():
    loader = DataLoader(data=[1, 2, 3, 4, 5], batch_size=2)
    assert len(loader) == 3


def test_iter_batches():
    loader = DataLoader(data=[1, 2, 3, 4, 5], batch_size=2)
    batches = list(loader)
    assert len(batches) == 3
    assert batches[0] == [1, 2]
    assert batches[-1] == [5]


def test_shuffle_changes_order():
    loader = DataLoader(data=list(range(10)), batch_size=10, shuffle=True)
    first = list(loader)[0]
    assert first != list(range(10))


def test_add():
    loader = DataLoader(data=[1, 2], batch_size=2)
    loader.add(3)
    assert len(loader) == 2
    batches = list(loader)
    assert batches[0] == [1, 2] or batches[0] == [2, 3]


def test_save_and_load(tmp_path):
    loader = DataLoader(data=[{"a": 1}, {"a": 2}], batch_size=1)
    loader.save(str(tmp_path / "data.json"))
    loaded = DataLoader.load(str(tmp_path / "data.json"))
    assert loaded.data == loader.data
    assert loaded.batch_size == 1


def test_empty_data():
    loader = DataLoader(data=[], batch_size=2)
    assert len(loader) == 0
    assert list(loader) == []


def test_single_batch():
    loader = DataLoader(data=[1, 2, 3], batch_size=5)
    batches = list(loader)
    assert len(batches) == 1
    assert batches[0] == [1, 2, 3]
