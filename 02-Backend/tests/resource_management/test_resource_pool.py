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
    # Identity, not inequality: the factory here is `list`, and three empty
    # lists compare equal to each other, so `a != b` is false even though the
    # pool really did hand out three separate resources.
    pool = ResourcePool(list, size=3)
    a = pool.acquire()
    b = pool.acquire()
    c = pool.acquire()
    assert a is not b
    assert b is not c
    assert a is not c
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
    first = pool.acquire()
    assert pool.available() == 1
    second = pool.acquire()
    assert pool.available() == 0
    # `pool.release(pool.acquire())` was here before: the inner acquire runs
    # with no timeout against an empty pool, so `Condition.wait(None)` blocks
    # forever and the whole suite hangs. Releasing a resource that is already
    # held expresses the same count.
    pool.release(first)
    assert pool.available() == 1
    pool.release(second)

