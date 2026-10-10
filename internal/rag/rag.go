// Package rag provides a Retrieval-Augmented Generation engine:
// chunking, embedding, retrieval, reranking, and prompt assembly.
package rag

import (
	"fmt"
	"math"
	"sort"
	"strings"
	"sync"

	"github.com/astrovox/astrovox/internal/vectordb"
)

// Chunk is a piece of a document with metadata.
type Chunk struct {
	ID       string
	Text     string
	StartIdx int
	EndIdx   int
	Metadata map[string]interface{}
	Vector   vectordb.Vector
}

// ChunkingStrategy identifies how text is split.
type ChunkingStrategy int

const (
	ChunkFixedSize ChunkingStrategy = iota
	ChunkSentence
	ChunkParagraph
	ChunkRecursive
)

// Chunker splits documents into chunks.
type Chunker struct {
	Strategy   ChunkingStrategy
	ChunkSize  int // target chunk size in characters
	Overlap    int // overlap between chunks
	Separators []string
}

// NewChunker creates a chunker.
func NewChunker(strategy ChunkingStrategy, size, overlap int) *Chunker {
	return &Chunker{
		Strategy:   strategy,
		ChunkSize:  size,
		Overlap:    overlap,
		Separators: []string{"\n\n", ". ", " "},
	}
}

// Chunk splits text into chunks.
func (c *Chunker) Chunk(docID, text string) []*Chunk {
	switch c.Strategy {
	case ChunkFixedSize:
		return c.chunkFixed(docID, text)
	case ChunkSentence:
		return c.chunkBySeparator(docID, text, []string{". ", "! ", "? "})
	case ChunkParagraph:
		return c.chunkBySeparator(docID, text, []string{"\n\n"})
	default:
		return c.chunkRecursive(docID, text, 0)
	}
}

func (c *Chunker) chunkFixed(docID, text string) []*Chunk {
	var chunks []*Chunk
	step := c.ChunkSize - c.Overlap
	if step <= 0 {
		step = c.ChunkSize
	}
	for i := 0; i < len(text); i += step {
		end := i + c.ChunkSize
		if end > len(text) {
			end = len(text)
		}
		chunks = append(chunks, &Chunk{
			ID:       fmt.Sprintf("%s#%d", docID, len(chunks)),
			Text:     text[i:end],
			StartIdx: i,
			EndIdx:   end,
			Metadata: map[string]interface{}{"doc": docID, "index": len(chunks)},
		})
		if end == len(text) {
			break
		}
	}
	return chunks
}

func (c *Chunker) chunkBySeparator(docID, text string, seps []string) []*Chunk {
	var parts []string
	switch len(seps) {
	case 0:
		parts = []string{text}
	case 1:
		parts = strings.Split(text, seps[0])
	default:
		parts = splitMulti(text, seps)
	}
	var chunks []*Chunk
	idx := 0
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p == "" {
			continue
		}
		chunks = append(chunks, &Chunk{
			ID:       fmt.Sprintf("%s#%d", docID, len(chunks)),
			Text:     p,
			StartIdx: idx,
			EndIdx:   idx + len(p),
			Metadata: map[string]interface{}{"doc": docID, "index": len(chunks)},
		})
		idx += len(p) + 1
	}
	return chunks
}

func (c *Chunker) chunkRecursive(docID, text string, depth int) []*Chunk {
	if len(text) <= c.ChunkSize || depth >= len(c.Separators) {
		if len(text) == 0 {
			return nil
		}
		return []*Chunk{{
			ID:       fmt.Sprintf("%s#%d", docID, 0),
			Text:     text,
			StartIdx: 0,
			EndIdx:   len(text),
			Metadata: map[string]interface{}{"doc": docID, "index": 0, "depth": depth},
		}}
	}
	sep := c.Separators[depth]
	parts := strings.Split(text, sep)
	var chunks []*Chunk
	cur := strings.Builder{}
	flush := func() {
		s := strings.TrimSpace(cur.String())
		if s != "" {
			chunks = append(chunks, &Chunk{
				ID:       fmt.Sprintf("%s#%d", docID, len(chunks)),
				Text:     s,
				StartIdx: 0,
				EndIdx:   len(s),
				Metadata: map[string]interface{}{"doc": docID, "index": len(chunks), "depth": depth},
			})
		}
		cur.Reset()
	}
	for _, p := range parts {
		if cur.Len()+len(p) > c.ChunkSize && cur.Len() > 0 {
			flush()
		}
		if cur.Len() > 0 {
			cur.WriteString(sep)
		}
		cur.WriteString(p)
		// If the accumulated text is still too long, flush and descend
		// into the next separator level.
		if cur.Len() > c.ChunkSize {
			flush()
		}
	}
	flush()
	// Re-chunk any oversized pieces with the next separator level.
	if depth+1 < len(c.Separators) {
		var final []*Chunk
		for _, ch := range chunks {
			if len(ch.Text) > c.ChunkSize {
				final = append(final, c.chunkRecursive(docID, ch.Text, depth+1)...)
			} else {
				final = append(final, ch)
			}
		}
		chunks = final
	}
	return chunks
}

func splitMulti(text string, seps []string) []string {
	// greedy split on the longest matching separator
	var out []string
	rest := text
	for len(rest) > 0 {
		best, bestPos := "", -1
		for _, s := range seps {
			if idx := strings.Index(rest, s); idx >= 0 && (bestPos < 0 || idx < bestPos) {
				best, bestPos = s, idx
			}
		}
		if bestPos < 0 {
			out = append(out, rest)
			break
		}
		if bestPos > 0 {
			out = append(out, rest[:bestPos])
		}
		rest = rest[bestPos+len(best):]
	}
	return out
}

// Embedder converts text into vectors.
type Embedder interface {
	Embed(text string) (vectordb.Vector, error)
	EmbedBatch(texts []string) ([]vectordb.Vector, error)
	Dimension() int
}

// SimpleEmbedder is a deterministic hash-based embedder used for testing
// and offline operation. It produces a bag-of-characters vector.
type SimpleEmbedder struct {
	dim    int
	mu     sync.Mutex
	vocab  map[string]int
	nextID int
}

// NewSimpleEmbedder creates a hashing-based embedder.
func NewSimpleEmbedder(dim int) *SimpleEmbedder {
	return &SimpleEmbedder{dim: dim, vocab: make(map[string]int)}
}

// Dimension returns the embedding dimension.
func (e *SimpleEmbedder) Dimension() int { return e.dim }

func (e *SimpleEmbedder) wordID(word string) int {
	e.mu.Lock()
	defer e.mu.Unlock()
	id, ok := e.vocab[word]
	if !ok {
		id = e.nextID % e.dim
		e.vocab[word] = id
		e.nextID++
	}
	return id
}

// Embed produces a deterministic bag-of-words vector.
func (e *SimpleEmbedder) Embed(text string) (vectordb.Vector, error) {
	v := make(vectordb.Vector, e.dim)
	for _, w := range strings.Fields(strings.ToLower(text)) {
		id := e.wordID(w)
		v[id] += 1.0
	}
	// L2 normalize so cosine similarity is meaningful
	var norm float64
	for _, x := range v {
		norm += x * x
	}
	if norm > 0 {
		norm = math.Sqrt(norm)
		for i := range v {
			v[i] /= norm
		}
	}
	return v, nil
}

// EmbedBatch embeds many texts.
func (e *SimpleEmbedder) EmbedBatch(texts []string) ([]vectordb.Vector, error) {
	out := make([]vectordb.Vector, 0, len(texts))
	for _, t := range texts {
		v, err := e.Embed(t)
		if err != nil {
			return nil, err
		}
		out = append(out, v)
	}
	return out, nil
}

// ScoredResult is a search hit with text.
type ScoredResult struct {
	ChunkID  string
	Text     string
	Score    float64
	Metadata map[string]interface{}
}

// Reranker reorders retrieval results by relevance.
type Reranker interface {
	Score(query string, text string) float64
}

// LexicalReranker ranks by term overlap between query and text.
type LexicalReranker struct{}

// NewLexicalReranker creates a lexical reranker.
func NewLexicalReranker() *LexicalReranker { return &LexicalReranker{} }

// Score computes normalized term overlap.
func (r *LexicalReranker) Score(query, text string) float64 {
	qTerms := termSet(query)
	if len(qTerms) == 0 {
		return 0
	}
	tTerms := termSet(text)
	hits := 0
	for t := range qTerms {
		if tTerms[t] {
			hits++
		}
	}
	return float64(hits) / float64(len(qTerms))
}

func termSet(s string) map[string]bool {
	out := make(map[string]bool)
	for _, w := range strings.Fields(strings.ToLower(s)) {
		w = strings.Trim(w, ".,!?;:\"'()[]{}")
		if len(w) > 2 {
			out[w] = true
		}
	}
	return out
}

// RAGEngine ties chunking, embedding, retrieval and reranking together.
type RAGEngine struct {
	chunker  *Chunker
	embedder Embedder
	db       *vectordb.VectorDB
	reranker Reranker
	topK     int
	rerankK  int
	mu       sync.RWMutex
	chunks   map[string]*Chunk
}

// NewRAGEngine creates a RAG engine.
func NewRAGEngine(chunker *Chunker, embedder Embedder, topK, rerankK int) (*RAGEngine, error) {
	db := vectordb.NewVectorDBWithIndex(vectordb.MetricCosine, embedder.Dimension())
	return &RAGEngine{
		chunker:  chunker,
		embedder: embedder,
		db:       db,
		reranker: NewLexicalReranker(),
		topK:     topK,
		rerankK:  rerankK,
		chunks:   make(map[string]*Chunk),
	}, nil
}

// SetReranker replaces the reranker.
func (r *RAGEngine) SetReranker(rr Reranker) { r.reranker = rr }

// Ingest chunks and indexes a document.
func (r *RAGEngine) Ingest(docID, text string) error {
	chunks := r.chunker.Chunk(docID, text)
	for _, c := range chunks {
		v, err := r.embedder.Embed(c.Text)
		if err != nil {
			return err
		}
		c.Vector = v
		if err := r.db.Insert(&vectordb.Document{
			ID:      c.ID,
			Vector:  v,
			Payload: c.Metadata,
		}); err != nil {
			return err
		}
		r.mu.Lock()
		r.chunks[c.ID] = c
		r.mu.Unlock()
	}
	return nil
}

// Retrieve returns the most relevant chunks for a query.
func (r *RAGEngine) Retrieve(query string, k int) ([]ScoredResult, error) {
	if k <= 0 {
		k = r.topK
	}
	qvec, err := r.embedder.Embed(query)
	if err != nil {
		return nil, err
	}
	hits, err := r.db.Search(qvec, k)
	if err != nil {
		return nil, err
	}
	out := make([]ScoredResult, 0, len(hits))
	for _, h := range hits {
		var text string
		r.mu.RLock()
		if c, ok := r.chunks[h.ID]; ok {
			text = c.Text
		}
		r.mu.RUnlock()
		out = append(out, ScoredResult{
			ChunkID:  h.ID,
			Text:     text,
			Score:    h.Score,
			Metadata: h.Payload,
		})
	}
	return out, nil
}

// Rerank reorders results using the reranker.
func (r *RAGEngine) Rerank(query string, results []ScoredResult) []ScoredResult {
	for i := range results {
		results[i].Score = r.reranker.Score(query, results[i].Text)
	}
	sort.Slice(results, func(i, j int) bool { return results[i].Score > results[j].Score })
	n := r.rerankK
	if n <= 0 || n > len(results) {
		n = len(results)
	}
	return results[:n]
}

// RetrieveAndRerank retrieves then reranks in one step.
func (r *RAGEngine) RetrieveAndRerank(query string) ([]ScoredResult, error) {
	hits, err := r.Retrieve(query, r.topK)
	if err != nil {
		return nil, err
	}
	return r.Rerank(query, hits), nil
}

// BuildPrompt assembles a prompt from the top context chunks.
func (r *RAGEngine) BuildPrompt(query string, context []ScoredResult) string {
	var sb strings.Builder
	sb.WriteString("Use the following context to answer the question.\n\n")
	sb.WriteString("Context:\n")
	for i, c := range context {
		sb.WriteString(fmt.Sprintf("[%d] %s\n\n", i+1, c.Text))
	}
	sb.WriteString("Question: ")
	sb.WriteString(query)
	sb.WriteString("\n\nAnswer:")
	return sb.String()
}

// Answer retrieves context and builds a prompt.
func (r *RAGEngine) Answer(query string) (string, error) {
	ctx, err := r.RetrieveAndRerank(query)
	if err != nil {
		return "", err
	}
	return r.BuildPrompt(query, ctx), nil
}

// Stats returns engine statistics.
func (r *RAGEngine) Stats() RAGStats {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return RAGStats{
		Chunks:    len(r.chunks),
		Documents: r.db.Len(),
		TopK:      r.topK,
		RerankK:   r.rerankK,
		Dimension: r.embedder.Dimension(),
	}
}

// RAGStats describes the engine state.
type RAGStats struct {
	Chunks    int
	Documents int
	TopK      int
	RerankK   int
	Dimension int
}
