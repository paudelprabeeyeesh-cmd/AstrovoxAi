from cache_coherence.version_vector import VersionVector


def test_increment():
    vv = VersionVector()
    vv.increment("node-a")
    vv.increment("node-a")
    assert vv._clock["node-a"] == 2


def test_merge():
    vv1 = VersionVector()
    vv1.increment("node-a")
    vv1._clock["node-a"] = 3

    vv2 = VersionVector()
    vv2.increment("node-a")
    vv2._clock["node-a"] = 5

    vv1.merge(vv2)
    assert vv1._clock["node-a"] == 5


def test_compare_true():
    vv1 = VersionVector()
    vv1.increment("node-a")
    vv1._clock["node-a"] = 5

    vv2 = VersionVector()
    vv2.increment("node-a")
    vv2._clock["node-a"] = 3

    assert vv2.compare(vv1) is True


def test_compare_false():
    vv1 = VersionVector()
    vv1.increment("node-a")
    vv1._clock["node-a"] = 3

    vv2 = VersionVector()
    vv2.increment("node-a")
    vv2._clock["node-a"] = 5

    assert vv2.compare(vv1) is False


def test_compare_empty_true():
    vv = VersionVector()
    other = VersionVector()
    other.increment("node-a")
    assert vv.compare(other) is True


def test_to_dict():
    vv = VersionVector()
    vv.increment("node-a")
    vv._clock["node-a"] = 7
    assert vv.to_dict()["node-a"] == 7


def test_from_dict():
    data = {"node-a": 7, "node-b": 3}
    vv = VersionVector.from_dict(data)
    assert vv._clock["node-a"] == 7
    assert vv._clock["node-b"] == 3


def test_copy():
    vv = VersionVector()
    vv.increment("node-a")
    vv._clock["node-a"] = 4

    vv2 = vv.copy()
    assert vv2._clock["node-a"] == 4
    assert vv2 is not vv


def test_is_concurrent_with():
    vv1 = VersionVector()
    vv1.increment("node-a")
    vv1._clock["node-a"] = 5

    vv2 = VersionVector()
    vv2.increment("node-a")
    vv2._clock["node-a"] = 3

    assert vv1.is_concurrent_with(vv2) is False


def test_update():
    vv = VersionVector()
    vv._clock["node-a"] = 3
    vv.update("node-a", 7)
    assert vv._clock["node-a"] == 7
    vv.update("node-a", 2)
    assert vv._clock["node-a"] == 7
