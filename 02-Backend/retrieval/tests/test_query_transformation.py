
from retrieval.query_transformation import QueryTransformer


def test_rewrite():
    transformer = QueryTransformer()
    result = transformer.transform("The quick brown fox", strategy="rewrite")
    assert result.strategy == "rewrite"
    assert result.original_query == "The quick brown fox"
    assert "the" not in result.transformed_query.lower().split()


def test_expand():
    transformer = QueryTransformer()
    result = transformer.transform("cat", strategy="expand")
    assert "cat" in result.transformed_query
    assert "cats" in result.transformed_query


def test_decompose():
    transformer = QueryTransformer()
    result = transformer.transform("python and java", strategy="decompose")
    parts = result.transformed_query.split(' | ')
    assert len(parts) == 2
    assert "python" in parts[0]
    assert "java" in parts[1]


def test_hyde():
    transformer = QueryTransformer()
    result = transformer.transform("how to cook pasta", strategy="hyde")
    assert "hypothetical answer to: how to cook pasta" == result.transformed_query


def test_passthrough():
    transformer = QueryTransformer()
    result = transformer.transform("some query", strategy="unknown")
    assert result.transformed_query == "some query"
    assert result.strategy == "passthrough"
