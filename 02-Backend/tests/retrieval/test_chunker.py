from retrieval.chunker import fixed_size_chunk, sentence_aware_chunk, paragraph_aware_chunk, hierarchical_chunk, Chunker, Document


def test_fixed_size_chunk():
    text = "abcdefghij"
    chunks = fixed_size_chunk(text, chunk_size=3, overlap=0)
    assert chunks == ["abc", "def", "ghi", "j"]


def test_fixed_size_chunk_overlap():
    text = "abcdefghij"
    chunks = fixed_size_chunk(text, chunk_size=3, overlap=1)
    assert len(chunks) > 1


def test_sentence_aware_chunk():
    text = "First sentence. Second sentence! Third sentence?"
    chunks = sentence_aware_chunk(text, max_chunk_size=50)
    assert len(chunks) == 1


def test_sentence_aware_chunk_overflow():
    text = "First sentence. Second sentence. Third sentence."
    chunks = sentence_aware_chunk(text, max_chunk_size=20)
    assert len(chunks) > 1


def test_paragraph_aware_chunk():
    text = "Para one.\n\nPara two.\n\nPara three."
    chunks = paragraph_aware_chunk(text)
    assert len(chunks) == 3


def test_hierarchical_chunk():
    text = "abcdefghij"
    result = hierarchical_chunk(text, levels=[3, 5])
    assert "level_1" in result
    assert "level_2" in result


def test_chunker_fixed():
    chunker = Chunker(strategy="fixed", chunk_size=2)
    chunks = chunker.chunk("abcd")
    assert len(chunks) == 2


def test_chunker_unknown():
    chunker = Chunker(strategy="unknown")
    chunks = chunker.chunk("text")
    assert chunks == ["text"]
