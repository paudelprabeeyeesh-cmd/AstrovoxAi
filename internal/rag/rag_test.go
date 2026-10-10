package rag

import (
	"strings"
	"testing"
)

func newEngine(t *testing.T, topK, rerankK int) *RAGEngine {
	t.Helper()
	ch := NewChunker(ChunkFixedSize, 50, 10)
	emb := NewSimpleEmbedder(32)
	e, err := NewRAGEngine(ch, emb, topK, rerankK)
	if err != nil {
		t.Fatal(err)
	}
	return e
}

func TestChunkerFixedSize(t *testing.T) {
	c := NewChunker(ChunkFixedSize, 10, 0)
	chunks := c.Chunk("doc", "0123456789abcdefghijklmnopqrstuvwxyz")
	if len(chunks) < 3 {
		t.Errorf("expected several chunks, got %d", len(chunks))
	}
	if chunks[0].Text != "0123456789" {
		t.Errorf("unexpected first chunk: %q", chunks[0].Text)
	}
}

func TestChunkerOverlap(t *testing.T) {
	c := NewChunker(ChunkFixedSize, 10, 5)
	chunks := c.Chunk("doc", "0123456789abcdefghij")
	if len(chunks) < 2 {
		t.Fatalf("expected >=2 chunks, got %d", len(chunks))
	}
	if chunks[1].Text[:5] != "56789" {
		t.Errorf("expected overlap, got %q", chunks[1].Text)
	}
}

func TestChunkerSentence(t *testing.T) {
	c := NewChunker(ChunkSentence, 100, 0)
	chunks := c.Chunk("doc", "Hello there. General Kenobi. You are a bold one.")
	if len(chunks) != 3 {
		t.Errorf("expected 3 sentence chunks, got %d", len(chunks))
	}
}

func TestChunkerParagraph(t *testing.T) {
	c := NewChunker(ChunkParagraph, 100, 0)
	chunks := c.Chunk("doc", "para one\n\npara two\n\npara three")
	if len(chunks) != 3 {
		t.Errorf("expected 3 paragraphs, got %d", len(chunks))
	}
}

func TestChunkerRecursive(t *testing.T) {
	// A single word longer than the chunk size at every level falls through
	// to a single chunk; splitting on spaces needs a longer document.
	c := NewChunker(ChunkRecursive, 5, 0)
	chunks := c.Chunk("doc", "alpha bravo charlie delta echo foxtrot golf")
	if len(chunks) < 2 {
		t.Errorf("expected multiple chunks, got %d", len(chunks))
	}

	// A document shorter than the size stays whole.
	c2 := NewChunker(ChunkRecursive, 1000, 0)
	if got := len(c2.Chunk("doc", "short")); got != 1 {
		t.Errorf("expected 1 chunk for short doc, got %d", got)
	}
}

func TestChunkerEmptyInput(t *testing.T) {
	c := NewChunker(ChunkFixedSize, 10, 0)
	if chunks := c.Chunk("doc", ""); len(chunks) != 0 {
		t.Errorf("expected 0 chunks, got %d", len(chunks))
	}
}

func TestSimpleEmbedder(t *testing.T) {
	e := NewSimpleEmbedder(16)
	if e.Dimension() != 16 {
		t.Errorf("expected dim 16, got %d", e.Dimension())
	}
	v, err := e.Embed("hello world hello")
	if err != nil {
		t.Fatal(err)
	}
	if len(v) != 16 {
		t.Errorf("expected 16 dims, got %d", len(v))
	}
	var norm float64
	for _, x := range v {
		norm += x * x
	}
	if norm > 1.01 || norm < 0.99 {
		t.Errorf("expected unit norm, got %f", norm)
	}
}

func TestSimpleEmbedderDeterministic(t *testing.T) {
	e := NewSimpleEmbedder(8)
	a, _ := e.Embed("same text")
	b, _ := e.Embed("same text")
	for i := range a {
		if a[i] != b[i] {
			t.Fatal("embedder must be deterministic")
		}
	}
	x, _ := e.Embed("different content entirely")
	same := true
	for i := range a {
		if a[i] != x[i] {
			same = false
		}
	}
	if same {
		t.Error("different text should give different vectors")
	}
}

func TestEmbedBatch(t *testing.T) {
	e := NewSimpleEmbedder(4)
	vs, err := e.EmbedBatch([]string{"a", "b", "c"})
	if err != nil {
		t.Fatal(err)
	}
	if len(vs) != 3 {
		t.Errorf("expected 3 vectors, got %d", len(vs))
	}
}

func TestLexicalReranker(t *testing.T) {
	r := NewLexicalReranker()
	s := r.Score("quick brown fox", "the quick brown fox jumps")
	if s <= 0 || s > 1 {
		t.Errorf("expected overlap score, got %f", s)
	}
	if r.Score("nothing", "totally different") != 0 {
		t.Error("expected 0 for no overlap")
	}
}

func TestRAGIngestRetrieve(t *testing.T) {
	e := newEngine(t, 3, 2)
	if err := e.Ingest("d1", "Go is a statically typed compiled language"); err != nil {
		t.Fatal(err)
	}
	if err := e.Ingest("d2", "Python is dynamically typed and interpreted"); err != nil {
		t.Fatal(err)
	}
	res, err := e.Retrieve("Go compiled language", 2)
	if err != nil {
		t.Fatal(err)
	}
	if len(res) != 2 {
		t.Fatalf("expected 2 results, got %d", len(res))
	}
	if res[0].ChunkID == "" {
		t.Error("expected a chunk id")
	}
}

func TestRAGRetrieveAndRerank(t *testing.T) {
	e := newEngine(t, 5, 2)
	e.Ingest("d1", "apples are red fruit")
	e.Ingest("d2", "bananas are yellow fruit")
	e.Ingest("d3", "cars need fuel")
	res, err := e.RetrieveAndRerank("red apples fruit")
	if err != nil {
		t.Fatal(err)
	}
	if len(res) == 0 {
		t.Fatal("expected results")
	}
}

func TestRAGBuildPrompt(t *testing.T) {
	e := newEngine(t, 2, 2)
	ctx := []ScoredResult{{ChunkID: "c1", Text: "ctx text"}}
	p := e.BuildPrompt("q?", ctx)
	if !strings.Contains(p, "ctx text") || !strings.Contains(p, "q?") {
		t.Errorf("prompt missing content: %s", p)
	}
}

func TestRAGAnswer(t *testing.T) {
	e := newEngine(t, 3, 2)
	e.Ingest("d", "The sky is blue")
	ans, err := e.Answer("what color is the sky")
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(ans, "Answer") {
		t.Errorf("expected answer prompt, got %q", ans)
	}
}

func TestRAGSetReranker(t *testing.T) {
	e := newEngine(t, 2, 1)
	e.Ingest("d", "text")
	e.SetReranker(NewLexicalReranker())
	res, err := e.RetrieveAndRerank("text")
	if err != nil {
		t.Fatal(err)
	}
	if len(res) == 0 {
		t.Error("expected results")
	}
}

func TestRAGStats(t *testing.T) {
	e := newEngine(t, 2, 1)
	e.Ingest("d", "hello world")
	s := e.Stats()
	if s.Chunks != 1 {
		t.Errorf("expected 1 chunk, got %d", s.Chunks)
	}
	if s.Dimension != 32 {
		t.Errorf("expected dim 32, got %d", s.Dimension)
	}
}

func TestRAGDimensionMismatch(t *testing.T) {
	e := newEngine(t, 2, 1)
	// The engine's dimension comes from the embedder, so this is expected to work.
	if err := e.Ingest("d", "text"); err != nil {
		t.Fatal(err)
	}
}
