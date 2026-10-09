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


def test_fixed_size_chunk_empty_string():
    chunks = fixed_size_chunk("", chunk_size=5, overlap=0)
    assert chunks == []


def test_fixed_size_chunk_no_loss():
    text = "abcdef"
    chunks = fixed_size_chunk(text, chunk_size=3, overlap=0)
    assert "".join(chunks) == text


def test_fixed_size_chunk_overlap_zero():
    text = "abcdef"
    chunks = fixed_size_chunk(text, chunk_size=2, overlap=0)
    assert chunks == ["ab", "cd", "ef"]


def test_fixed_size_chunk_full_overlap():
    text = "abcdef"
    chunks = fixed_size_chunk(text, chunk_size=3, overlap=3)
    assert len(chunks) == 2
    assert chunks[0] == "abc"
    assert chunks[1] == "def"


def test_sentence_aware_chunk_empty():
    chunks = sentence_aware_chunk("", max_chunk_size=50)
    assert chunks == [""]


def test_sentence_aware_chunk_no_punctuation():
    text = "Hello world this is a test"
    chunks = sentence_aware_chunk(text, max_chunk_size=100)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_sentence_aware_chunk_returns_original_on_no_sentences():
    text = "   \n\t  "
    chunks = sentence_aware_chunk(text, max_chunk_size=50)
    assert chunks == [text]


def test_paragraph_aware_chunk_empty():
    chunks = paragraph_aware_chunk("")
    assert chunks == [""]


def test_paragraph_aware_chunk_single_paragraph():
    text = "Only one paragraph here."
    chunks = paragraph_aware_chunk(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_paragraph_aware_chunk_leading_trailing_newlines():
    text = "\n\nPara one.\n\nPara two.\n\n"
    chunks = paragraph_aware_chunk(text)
    assert len(chunks) == 2


def test_hierarchical_chunk_default_levels():
    text = "abcdefghij"
    result = hierarchical_chunk(text)
    assert "level_1" in result
    assert "level_2" in result


def test_chunker_strategy_sentence():
    chunker = Chunker(strategy="sentence", max_chunk_size=50)
    text = "First sentence. Second sentence."
    chunks = chunker.chunk(text)
    assert len(chunks) >= 1


def test_chunker_strategy_paragraph():
    chunker = Chunker(strategy="paragraph")
    text = "Para one.\n\nPara two."
    chunks = chunker.chunk(text)
    assert len(chunks) == 2


def test_chunker_strategy_hierarchical():
    chunker = Chunker(strategy="hierarchical")
    text = "abcdefghij"
    chunks = chunker.chunk(text)
    assert isinstance(chunks, list)
    assert len(chunks) >= 1
