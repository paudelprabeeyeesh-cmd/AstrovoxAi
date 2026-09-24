from differential_privacy.query_releaser import QueryReleaser
from differential_privacy.laplace_mechanism import LaplaceMechanism


def test_query_releaser_scalar():
    mechanism = LaplaceMechanism(sensitivity=1.0, epsilon=1.0)
    releaser = QueryReleaser(mechanism)

    def query():
        return 5.0

    released = releaser.release(query)
    assert isinstance(released, float)
    assert released != 5.0


def test_query_releaser_iterable():
    mechanism = LaplaceMechanism(sensitivity=1.0, epsilon=1.0)
    releaser = QueryReleaser(mechanism)

    def query():
        return [1.0, 2.0, 3.0]

    released = releaser.release(query)
    assert len(released) == 3
    for r in released:
        assert r != 1.0
        assert r != 2.0
        assert r != 3.0
