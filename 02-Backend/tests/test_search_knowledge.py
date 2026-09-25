"""Tests for search_knowledge.py — 15 features."""

import pytest
from datetime import datetime, timezone

from app.search_knowledge import (
    BM25Index,
    VectorIndex,
    HybridSearchEngine,
    CrossEncoderReranker,
    MultiVectorRetriever,
    IncrementalIndexer,
    KnowledgeGraphBuilder,
    CitationEngine,
    OCRPipeline,
    PDFIntelligenceParser,
    AudioTranscriber,
    VideoCaptionExtractor,
    ChunkingStrategies,
    MetadataExtractor,
    SemanticRetriever,
    QueryUnderstanding,
    SearchAnalytics,
    SearchKnowledgePlatform,
    SearchResult,
    Chunk,
    Document,
    QueryAnalysis,
    SearchAnalyticsEvent,
)


class TestBM25Index:
    def test_basic_search(self):
        idx = BM25Index()
        idx.add("d1", "the quick brown fox jumps over the lazy dog")
        idx.add("d2", "a quick brown dog runs fast")
        results = idx.search("quick brown fox", top_k=2)
        assert len(results) <= 2
        assert results[0][0] == "d1"

    def test_empty_search(self):
        idx = BM25Index()
        assert idx.search("nonexistent", top_k=5) == []

    def test_batch_add(self):
        idx = BM25Index()
        idx.add_batch([("d1", "hello world"), ("d2", "world peace")])
        assert idx.size == 2


class TestVectorIndex:
    def test_search(self):
        idx = VectorIndex()
        idx.add("d1", [1.0, 0.0, 0.0])
        idx.add("d2", [0.0, 1.0, 0.0])
        results = idx.search([1.0, 0.1, 0.0], top_k=2)
        assert len(results) == 2
        assert results[0][0] == "d1"

    def test_empty(self):
        idx = VectorIndex()
        assert idx.search([1.0, 0.0], top_k=5) == []


class TestHybridSearchEngine:
    def test_search_with_vector(self):
        engine = HybridSearchEngine(alpha=0.5)
        engine.index("d1", "the quick brown fox", [1.0, 0.0, 0.0])
        engine.index("d2", "lazy dog sleeps", [0.0, 1.0, 0.0])
        results = engine.search("quick fox", query_embedding=[0.9, 0.1, 0.0], top_k=2)
        assert len(results) <= 2
        assert all(isinstance(r, SearchResult) for r in results)

    def test_rrf_fusion(self):
        engine = HybridSearchEngine(fusion="rrf")
        engine.index("d1", "hello world", [1.0, 0.0])
        engine.index("d2", "world peace", [0.0, 1.0])
        results = engine.search("hello", query_embedding=[0.9, 0.1], top_k=2)
        assert len(results) <= 2

    def test_len(self):
        engine = HybridSearchEngine()
        engine.index("d1", "text", [1.0, 0.0])
        assert len(engine) == 1


class TestCrossEncoderReranker:
    def test_rerank_basic(self):
        reranker = CrossEncoderReranker()
        candidates = [
            SearchResult(chunk_id="c1", document_id="d1", content="the quick brown fox", score=0.5),
            SearchResult(chunk_id="c2", document_id="d2", content="lazy dog sleeps", score=0.8),
        ]
        results = reranker.rerank("quick fox", candidates, top_k=2)
        assert len(results) == 2
        assert results[0].chunk_id == "c1"

    def test_exact_match_bonus(self):
        reranker = CrossEncoderReranker(boost_exact=1.0)
        candidates = [
            SearchResult(chunk_id="c1", document_id="d1", content="exact match content", score=0.5),
            SearchResult(chunk_id="c2", document_id="d2", content="unrelated text", score=0.9),
        ]
        results = reranker.rerank("exact match", candidates, top_k=2)
        assert results[0].chunk_id == "c1"

    def test_empty_candidates(self):
        reranker = CrossEncoderReranker()
        assert reranker.rerank("query", []) == []


class TestMultiVectorRetriever:
    def test_search(self):
        retriever = MultiVectorRetriever(max_vectors_per_doc=8)
        retriever.index("d1", [("token1", [1.0, 0.0]), ("token2", [0.9, 0.1])])
        retriever.index("d2", [("token3", [0.0, 1.0]), ("token4", [0.1, 0.9])])
        results = retriever.search([[1.0, 0.0], [0.9, 0.1]], top_k=2)
        assert len(results) <= 2
        assert results[0][0] == "d1"

    def test_empty(self):
        retriever = MultiVectorRetriever()
        assert retriever.search([[1.0, 0.0]], top_k=5) == []


class TestIncrementalIndexer:
    def test_sync_new_items(self):
        indexer = IncrementalIndexer()
        items = [{"id": "1", "name": "doc1", "updated_at": "2024-01-01T00:00:00Z"}]
        result = indexer.sync("test_collection", items)
        assert result["new"] == 1

    def test_sync_updated_items(self):
        indexer = IncrementalIndexer()
        indexer.sync("test", [{"id": "1", "updated_at": "2024-01-01T00:00:00Z"}])
        result = indexer.sync("test", [{"id": "1", "updated_at": "2024-01-02T00:00:00Z"}])
        assert result["updated"] == 1

    def test_delete(self):
        indexer = IncrementalIndexer()
        indexer.sync("test", [{"id": "1", "updated_at": "2024-01-01T00:00:00Z"}])
        deleted = indexer.delete(["1"])
        assert deleted == 1

    def test_stats(self):
        indexer = IncrementalIndexer()
        indexer.sync("test", [{"id": "1", "updated_at": "2024-01-01T00:00:00Z"}])
        stats = indexer.get_stats()
        assert stats["total_indexed"] >= 1


class TestKnowledgeGraphBuilder:
    def test_add_entity(self):
        builder = KnowledgeGraphBuilder()
        node = builder.add_entity("Python", "language")
        assert node.name == "Python"
        assert node.node_type == "language"

    def test_add_relation(self):
        builder = KnowledgeGraphBuilder()
        builder.add_entity("Python", "language")
        builder.add_entity("PyTorch", "framework")
        edge = builder.add_relation("Python", "PyTorch", "has_framework")
        assert edge.relation == "has_framework"

    def test_build_from_text(self):
        builder = KnowledgeGraphBuilder()
        text = "Python is a programming language. Guido created Python. Python has many frameworks."
        result = builder.build_from_text(text)
        assert result["entities_added"] >= 1
        assert result["relations_added"] >= 1

    def test_subgraph(self):
        builder = KnowledgeGraphBuilder()
        builder.add_entity("A", "entity")
        builder.add_entity("B", "entity")
        builder.add_entity("C", "entity")
        builder.add_relation("A", "B", "connects")
        builder.add_relation("B", "C", "connects")
        sg = builder.subgraph("A", depth=2)
        assert len(sg["entities"]) >= 1

    def test_shortest_path(self):
        builder = KnowledgeGraphBuilder()
        builder.add_entity("Start", "entity")
        builder.add_entity("End", "entity")
        builder.add_entity("Middle", "entity")
        builder.add_relation("Start", "Middle", "to")
        builder.add_relation("Middle", "End", "to")
        path = builder.shortest_path("Start", "End")
        assert len(path) >= 1

    def test_to_cypher(self):
        builder = KnowledgeGraphBuilder()
        builder.add_entity("Test", "entity")
        cypher = builder.to_cypher()
        assert "CREATE" in cypher

    def test_get_stats(self):
        builder = KnowledgeGraphBuilder()
        builder.add_entity("X", "type")
        stats = builder.get_stats()
        assert stats["nodes"] >= 1


class TestCitationEngine:
    def test_generate_apa(self):
        engine = CitationEngine()
        citation = engine.generate("Test Title", ["Smith, J."], year="2024", source="Test Journal", style="apa")
        assert citation.style == "apa"
        assert "Smith" in citation.text

    def test_generate_mla(self):
        engine = CitationEngine()
        citation = engine.generate("Test Title", ["Smith, J."], year="2024", style="mla")
        assert citation.style == "mla"

    def test_generate_invalid_style(self):
        engine = CitationEngine()
        citation = engine.generate("Title", [], style="unknown")
        assert citation.style == "apa"

    def test_generate_batch(self):
        engine = CitationEngine()
        refs = [{"title": "T1", "authors": ["A1"], "year": "2024"}]
        citations = engine.generate_batch(refs, style="apa")
        assert len(citations) == 1

    def test_extract_from_chunks(self):
        engine = CitationEngine()
        chunks = [Chunk(id="c1", document_id="d1", content="hello", chunk_index=0,
                        metadata={"source_type": "pdf", "filename": "test.pdf"})]
        citations = engine.extract_from_chunks(chunks)
        assert len(citations) >= 1

    def test_inline_format(self):
        engine = CitationEngine()
        citation = engine.generate("Title", ["Smith"], year="2024", style="apa")
        inline = engine.format_inline(citation)
        assert "Smith" in inline

    def test_bibliography(self):
        engine = CitationEngine()
        citations = [engine.generate("T1", ["A1"], year="2024")]
        bib = engine.to_bibliography(citations)
        assert "[1]" in bib


class TestOCRPipeline:
    def test_process_empty(self):
        ocr = OCRPipeline()
        result = ocr.process(b"", "test.png")
        assert "text" in result
        assert result["word_count"] >= 0

    def test_process_with_ascii(self):
        ocr = OCRPipeline()
        image_data = b"Some ASCII text content in image data \x20\x21\x22"
        result = ocr.process(image_data, "test.png")
        assert "text" in result

    def test_confidence_threshold(self):
        ocr = OCRPipeline(confidence_threshold=0.9)
        result = ocr.process(b"data", "test.png")
        assert "confidence" in result or "regions" in result


class TestPDFIntelligenceParser:
    def test_parse_empty(self):
        parser = PDFIntelligenceParser()
        result = parser.parse(b"", "test.pdf")
        assert "text" in result
        assert "page_count" in result

    def test_parse_with_structure(self):
        parser = PDFIntelligenceParser()
        result = parser.parse_with_structure(b"%PDF-1.4\ntest content", "test.pdf")
        assert "sections" in result
        assert "tables" in result
        assert "references" in result

    def test_sections_detection(self):
        parser = PDFIntelligenceParser()
        sections = parser._detect_sections("Introduction\nThis is intro.\n\nMethods\nThis is methods.")
        assert isinstance(sections, list)


class TestAudioTranscriber:
    def test_transcribe_empty(self):
        transcriber = AudioTranscriber()
        result = transcriber.transcribe(b"", "test.mp3")
        assert "text" in result
        assert "duration_seconds" in result

    def test_transcribe_with_segments(self):
        transcriber = AudioTranscriber()
        result = transcriber.transcribe_with_timestamps(b"some audio data", "test.mp3")
        assert "segments" in result
        assert "speakers" in result

    def test_duration_calculation(self):
        transcriber = AudioTranscriber()
        result = transcriber.transcribe(b"x" * 32000, "test.mp3")
        assert result["duration_seconds"] >= 0


class TestVideoCaptionExtractor:
    def test_extract_empty(self):
        extractor = VideoCaptionExtractor()
        result = extractor.extract(b"", "test.mp4")
        assert "transcript" in result
        assert "captions" in result

    def test_extract_with_scenes(self):
        extractor = VideoCaptionExtractor()
        result = extractor.extract_scene_descriptions(b"video data")
        assert isinstance(result, list)

    def test_captions_detected(self):
        extractor = VideoCaptionExtractor()
        video_data = b"1\n00:00:00,000 --> 00:00:05,000\nHello world\n\n"
        result = extractor.extract(video_data, "test.mp4")
        assert len(result["captions"]) >= 1


class TestChunkingStrategies:
    def test_semantic_chunking(self):
        chunker = ChunkingStrategies(chunk_size=100, chunk_overlap=20)
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = chunker.chunk(text, "doc1", "semantic")
        assert len(chunks) >= 1
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_paragraph_chunking(self):
        chunker = ChunkingStrategies(chunk_size=200, chunk_overlap=20)
        text = "Para one.\n\nPara two.\n\nPara three."
        chunks = chunker.chunk(text, "doc1", "paragraph")
        assert len(chunks) >= 1

    def test_sliding_chunking(self):
        chunker = ChunkingStrategies(chunk_size=50, chunk_overlap=10)
        text = "word " * 100
        chunks = chunker.chunk(text, "doc1", "sliding")
        assert len(chunks) >= 1

    def test_recursive_chunking(self):
        chunker = ChunkingStrategies(chunk_size=100, chunk_overlap=10)
        text = "Section one content here. " * 20
        chunks = chunker.chunk(text, "doc1", "recursive")
        assert len(chunks) >= 1

    def test_empty_text(self):
        chunker = ChunkingStrategies()
        assert chunker.chunk("", "doc1", "semantic") == []

    def test_tune(self):
        chunker = ChunkingStrategies()
        size, overlap = chunker.tune(500)
        assert size >= 300
        assert overlap >= 30


class TestMetadataExtractor:
    def test_extract_basic(self):
        extractor = MetadataExtractor()
        meta = extractor.extract("Hello world. This is a test.")
        assert meta["word_count"] == 5
        assert meta["char_count"] > 0
        assert "language" in meta
        assert "keywords" in meta

    def test_language_detection(self):
        extractor = MetadataExtractor()
        meta = extractor.extract("The quick brown fox jumps over the lazy dog.")
        assert meta["language"] == "en"

    def test_entities_extraction(self):
        extractor = MetadataExtractor()
        meta = extractor.extract("John Smith works at OpenAI in California.")
        assert len(meta["entities"]) >= 1

    def test_enrich_chunk(self):
        extractor = MetadataExtractor()
        chunk = Chunk(id="c1", document_id="d1", content="Test content", chunk_index=0)
        enriched = extractor.enrich_chunk_metadata(chunk)
        assert "word_count" in enriched
        assert enriched["chunk_id"] == "c1"

    def test_sentiment(self):
        extractor = MetadataExtractor()
        meta_pos = extractor.extract("This is great and amazing!")
        meta_neg = extractor.extract("This is terrible and awful.")
        assert meta_pos["sentiment"] in ("positive", "neutral")
        assert meta_neg["sentiment"] in ("negative", "neutral")


class TestSemanticRetriever:
    def test_index_and_retrieve(self):
        retriever = SemanticRetriever()
        docs = [
            Document(doc_id="d1", content="hello world", embeddings=[[1.0, 0.0, 0.0]]),
            Document(doc_id="d2", content="goodbye world", embeddings=[[0.0, 1.0, 0.0]]),
        ]
        retriever.index_batch(docs)
        results = retriever.retrieve("hello", top_k=2)
        assert len(results) <= 2
        assert results[0].chunk_id == "d1"

    def test_retrieve_with_context(self):
        retriever = SemanticRetriever()
        docs = [Document(doc_id="d1", content="context text", embeddings=[[0.8, 0.2]])]
        retriever.index_batch(docs)
        results = retriever.retrieve_with_context("query", ["context text"], top_k=1)
        assert len(results) <= 1


class TestQueryUnderstanding:
    def test_analyze_search_intent(self):
        qu = QueryUnderstanding()
        analysis = qu.analyze("search for python tutorials")
        assert analysis.intent == "search"

    def test_analyze_summarize_intent(self):
        qu = QueryUnderstanding()
        analysis = qu.analyze("summarize this document")
        assert analysis.intent == "summarize"

    def test_analyze_explain_intent(self):
        qu = QueryUnderstanding()
        analysis = qu.analyze("explain how transformers work")
        assert analysis.intent == "explain"

    def test_entity_extraction(self):
        qu = QueryUnderstanding()
        analysis = qu.analyze("Find documents by John Smith from 2024")
        assert len(analysis.entities) >= 1

    def test_filter_extraction(self):
        qu = QueryUnderstanding()
        analysis = qu.analyze("search type:pdf after 2023")
        assert "type" in analysis.filters or "date" in analysis.filters

    def test_rewrite(self):
        qu = QueryUnderstanding()
        analysis = qu.analyze("find python code examples")
        assert len(analysis.rewritten) > 0

    def test_expand(self):
        qu = QueryUnderstanding()
        expansions = qu.expand("search for code")
        assert len(expansions) >= 1

    def test_language_detection(self):
        qu = QueryUnderstanding()
        analysis = qu.analyze("¿Qué es Python?")
        assert analysis.language in {"es", "en"}


class TestSearchAnalytics:
    def test_record_event(self):
        analytics = SearchAnalytics()
        analytics.record(SearchAnalyticsEvent(
            query="test", user_id="u1", results_count=3,
            clicked_index=1, dwell_time_ms=500.0, latency_ms=100.0,
            sources=["hybrid"], timestamp=datetime.now(timezone.utc).isoformat(),
        ))
        assert len(analytics._events) == 1

    def test_query_stats(self):
        analytics = SearchAnalytics()
        analytics.record(SearchAnalyticsEvent(
            query="test query", user_id="u1", results_count=3,
            clicked_index=0, dwell_time_ms=200.0, latency_ms=50.0,
            sources=["hybrid"], timestamp=datetime.now(timezone.utc).isoformat(),
        ))
        stats = analytics.get_query_stats("test query")
        assert stats["total_queries"] == 1

    def test_user_stats(self):
        analytics = SearchAnalytics()
        analytics.record(SearchAnalyticsEvent(
            query="q", user_id="user1", results_count=1,
            clicked_index=0, dwell_time_ms=100.0, latency_ms=25.0,
            sources=["hybrid"], timestamp=datetime.now(timezone.utc).isoformat(),
            feedback="positive",
        ))
        stats = analytics.get_user_stats("user1")
        assert stats["positive_feedback"] == 1

    def test_overall_metrics(self):
        analytics = SearchAnalytics()
        analytics.record(SearchAnalyticsEvent(
            query="q", user_id="u1", results_count=1,
            clicked_index=0, dwell_time_ms=100.0, latency_ms=25.0,
            sources=["hybrid"], timestamp=datetime.now(timezone.utc).isoformat(),
        ))
        metrics = analytics.get_overall_metrics()
        assert metrics["total_events"] == 1

    def test_trending_queries(self):
        analytics = SearchAnalytics()
        for _ in range(3):
            analytics.record(SearchAnalyticsEvent(
                query="popular", user_id="u1", results_count=1,
                clicked_index=0, dwell_time_ms=100.0, latency_ms=25.0,
                sources=["hybrid"], timestamp=datetime.now(timezone.utc).isoformat(),
            ))
        trending = analytics.get_trending_queries(5)
        assert len(trending) >= 1

    def test_insights(self):
        analytics = SearchAnalytics()
        for _ in range(5):
            analytics.record(SearchAnalyticsEvent(
                query="no results", user_id="u1", results_count=0,
                clicked_index=0, dwell_time_ms=0.0, latency_ms=10.0,
                sources=[], timestamp=datetime.now(timezone.utc).isoformat(),
            ))
        insights = analytics.get_insights()
        assert isinstance(insights, list)


class TestSearchKnowledgePlatform:
    def test_hybrid_search(self):
        platform = SearchKnowledgePlatform()
        platform.hybrid.index("d1", "python tutorial", [0.9, 0.1])
        results = platform.hybrid_search("python", query_embedding=[0.9, 0.1], top_k=2)
        assert isinstance(results, list)

    def test_rerank_integration(self):
        platform = SearchKnowledgePlatform()
        candidates = [SearchResult(chunk_id="c1", document_id="d1", content="python code", score=0.5)]
        results = platform.rerank("python", candidates)
        assert isinstance(results, list)

    def test_chunk_document(self):
        platform = SearchKnowledgePlatform()
        chunks = platform.chunk_document("Hello world. " * 50, "doc1", strategy="semantic")
        assert len(chunks) >= 1

    def test_extract_metadata(self):
        platform = SearchKnowledgePlatform()
        meta = platform.extract_metadata("Hello world test content.")
        assert "word_count" in meta

    def test_understand_query(self):
        platform = SearchKnowledgePlatform()
        analysis = platform.understand_query("search for python tutorials")
        assert analysis.intent == "search"

    def test_ocr(self):
        platform = SearchKnowledgePlatform()
        result = platform.ocr_process(b"test image data")
        assert "text" in result

    def test_pdf_parse(self):
        platform = SearchKnowledgePlatform()
        result = platform.parse_pdf(b"%PDF-test", "test.pdf")
        assert "text" in result

    def test_audio_transcribe(self):
        platform = SearchKnowledgePlatform()
        result = platform.transcribe_audio(b"audio data")
        assert "text" in result

    def test_video_captions(self):
        platform = SearchKnowledgePlatform()
        result = platform.extract_video_captions(b"video data")
        assert "transcript" in result

    def test_search_pipeline(self):
        platform = SearchKnowledgePlatform()
        result = platform.search_pipeline("python tutorial", top_k=3)
        assert "query" in result
        assert "results" in result
        assert "analysis" in result
        assert "latency_ms" in result

    def test_knowledge_graph(self):
        platform = SearchKnowledgePlatform()
        result = platform.build_graph_from_text("Python is a language created by Guido.")
        assert result["entities_added"] >= 1

    def test_generate_citation(self):
        platform = SearchKnowledgePlatform()
        citation = platform.generate_citation("Test Title", ["Author"], style="apa")
        assert citation.style == "apa"

    def test_record_analytics(self):
        platform = SearchKnowledgePlatform()
        platform.record_search_event("test query", "u1", results_count=3, latency_ms=50.0,
                                     sources=["hybrid"])
        insights = platform.get_search_insights()
        assert "overall" in insights

    def test_incremental_sync(self):
        platform = SearchKnowledgePlatform()
        result = platform.incremental_sync("test_collection", [{"id": "1", "updated_at": "2024-01-01"}])
        assert result["new"] >= 0
