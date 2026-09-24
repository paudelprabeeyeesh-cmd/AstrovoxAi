import pytest
from resource_management import ResourcePool


def test_acquire_release():
    pool = ResourcePool(list, size=2)
    a = pool.acquire()
    b = pool.acquire()
    assert a is not None
    assert b is not None
    pool.release(a)
    pool.release(b)
    assert pool.available() == 2


def test_exhaust_pool_blocks():
    pool = ResourcePool(list, size=1)
    a = pool.acquire()
    assert a is not None
    with pytest.raises(Exception):
        pool.acquire(timeout=1)
    pool.release(a)


def test_initializes_with_requested_size():
    pool = ResourcePool(list, size=3)
    assert pool.available() == 3


def test_acquire_returns_distinct_items():
    pool = ResourcePool(list, size=3)
    a = pool.acquire()
    b = pool.acquire()
    c = pool.acquire()
    assert a != b
    assert b != c
    assert a != c
    pool.release(a)
    pool.release(b)
    pool.release(c)


def test_released_resource_is_reacquired():
    pool = ResourcePool(object, size=1)
    a = pool.acquire()
    pool.release(a)
    b = pool.acquire()
    assert b is a


def test_factory_called_for_each_resource():
    created = []

    def factory():
        obj = object()
        created.append(obj)
        return obj

    pool = ResourcePool(factory, size=3)
    assert len(created) == 3
    assert pool.available() == 3


def test_available_reflects_partial_usage():
    pool = ResourcePool(list, size=2)
    assert pool.available() == 2
    pool.acquire()
    assert pool.available() == 1
    pool.acquire()
    assert pool.available() == 0
    pool.release(pool.acquire())
    assert pool.available() == 1

