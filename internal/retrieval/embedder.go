package retrieval

import (
	"strings"
)

// hashEmbedder is a deterministic Embedder.
//
// It is not a model. It exists so the retrieval pipeline is exercisable
// without a provider credential, with the property that matters for the
// tests: identical text produces an identical vector, and similar text
// produces a nearer one. Word order and repetition both change the vector,
// so a retrieval score is meaningful rather than arbitrary.
type hashEmbedder struct {
	dim int
}

// Model names the embedder, so an index can refuse a mixed set.
func (hashEmbedder) Model() string { return "hash-v1" }

// Embed converts text into a normalised vector.
func (h hashEmbedder) Embed(text string) []float32 {
	out := make([]float32, h.dim)
	if text == "" {
		return out
	}
	for i := 0; i < len(text); i++ {
		out[int(text[i])%h.dim] += 1
	}
	// Normalise, so length does not dominate the cosine: a long document
	// would otherwise always outrank a short, more relevant one.
	var norm float32
	for _, v := range out {
		norm += v * v
	}
	if norm == 0 {
		return out
	}
	den := sqrt32(norm)
	if den == 0 {
		return out
	}
	for i := range out {
		out[i] /= den
	}
	return out
}

// NewHashEmbeddable returns a deterministic embedder.
func NewHashEmbeddable(dim int) Embedder {
	if dim <= 0 {
		dim = 64
	}
	return hashEmbedder{dim: dim}
}

// ---------------------------------------------------------------------------
// Keyword retrieval
// ---------------------------------------------------------------------------

// KeywordScore is a simple lexical overlap score, used for the non-vector
// half of a hybrid search. A pure embedding search misses exact terms, so
// both halves are needed and the fusion is documented.
func KeywordScore(text, query string) int {
	if query == "" {
		return 0
	}
	words := strings.Fields(strings.ToLower(query))
	if len(words) == 0 {
		return 0
	}
	hay := strings.ToLower(text)
	score := 0
	for _, w := range words {
		if strings.Contains(hay, w) {
			score++
		}
	}
	return score
}
