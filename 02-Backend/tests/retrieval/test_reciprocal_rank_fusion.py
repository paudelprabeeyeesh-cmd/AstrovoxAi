from retrieval.reciprocal_rank_fusion import reciprocal_rank_fusion


def test_rrf_empty():
    assert reciprocal_rank_fusion([]) == []


def test_rrf_single_list():
    ranked = [("a", 0.9), ("b", 0.8)]
    results = reciprocal_rank_fusion([ranked])
    assert len(results) == 2
    assert results[0][0] == "a"
    assert results[0][1] > results[1][1]


def test_rrf_multiple_lists():
    list1 = [("a", 1.0), ("b", 0.9)]
    list2 = [("b", 1.0), ("a", 0.8)]
    results = reciprocal_rank_fusion([list1, list2])
    assert len(results) == 2
    assert results[0][0] == "b"
    assert results[1][0] == "a"


def test_rrf_weights():
    list1 = [("a", 1.0)]
    list2 = [("b", 1.0)]
    results = reciprocal_rank_fusion([list1, list2], weights=[1.0, 2.0])
    assert results[0][0] == "b"


def test_rrf_deduplication():
    list1 = [("a", 1.0)]
    list2 = [("a", 0.5)]
    results = reciprocal_rank_fusion([list1, list2])
    assert len(results) == 1
    assert results[0][0] == "a"
