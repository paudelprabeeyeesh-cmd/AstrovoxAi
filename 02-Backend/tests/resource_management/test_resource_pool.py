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
        pool.acquire()
    pool.release(a)

