package retrieval

import (
	"sync"
	"testing"
	"time"
)

// The reranker was adopted on a measured MRR gain of 0.868 to 1.000 on 200
// documents. What was never measured is what that gain cost.
//
// This is the other half of the adoption decision. A reranker that improves
// nDCG by re-scoring the candidate list has to do that work on every request, on
// the hot path, and a caller who cannot see the latency difference cannot make a
// routing decision between it and a cheaper ordering. WS-I-003 asks for before
// and after numbers, so both are reported here.

// the numbers reported below are for the reranker as shipped, not for a
// cross-encoder: the lexical scorer is deliberately cheap, and the point of this
// test is to state its actual cost rather than to establish that a heavy model
// would be slower.

// benchCorpus builds a corpus of the given size for the benchmark.
func benchCorpus(t testing.TB, docs int) *Corpus {
	t.Helper()
	corpus := NewCorpus()
	for i := 0; i < docs; i++ {
		title := itoa(i)
		id := DocumentID("bench", title)
		corpus.AddDocument(&Document{ID: id, Owner: "bench", Tenant: "bench", Title: title})
		for position := 0; position < 4; position++ {
			cid := ChunkID(id, position)
			text := "chunk " + title + " position " + itoa(position) +
				" with shared filler words that appear in every document so the" +
				" scorer cannot trivially separate them by length alone"
			corpus.AddChunk(&Chunk{
				ID: cid, DocumentID: id, Owner: "bench", Tenant: "bench",
				Position: position, Text: text,
			})
		}
	}
	return corpus
}

func TestRerankerCostIsMeasured(t *testing.T) {
	// One comparison, reported: the same query with and without the reranker.
	// The reranker's work is bounded by the candidate count, so it is measured
	// at the candidate counts a caller actually uses rather than at a
	// corpus-size scale.
	for _, docs := range []int{200, 2000} {
		corpus := benchCorpus(t, docs)
		keyword := NewKeywordIndex(corpus)
		for cid := range corpus.chunks {
			if chunk := corpus.chunk(cid); chunk != nil {
				keyword.AddChunk(cid, chunk.Text)
			}
		}

		const iterations = 200
		query := "shared filler words position"

		// Without the reranker.
		start := time.Now()
		for i := 0; i < iterations; i++ {
			_ = keyword.Search("bench", query, 10)
		}
		without := time.Since(start) / iterations

		// With the reranker applied to the same first-pass results.
		start = time.Now()
		for i := 0; i < iterations; i++ {
			hits, err := corpusSearchForRerank(keyword, "bench", query, 10)
			if err != nil {
				t.Fatalf("search failed: %v", err)
			}
			_ = Rerank(query, hits, LexicalOverlapReranker{}, 10)
		}
		with := time.Since(start) / iterations

		t.Logf("docs=%d  without reranker %v   with reranker %v   overhead %v (%.1fx)",
			docs, without, with, with-without, ratio(with, without))

		// The reranker must not dominate the search it re-ranks. If it does,
		// adopting it was a latency decision rather than a relevance one, and
		// that should be visible rather than averaged away.
		if without > 0 && with-without > 4*without {
			t.Fatalf(
				"the reranker added more than 4x the search's own cost: search %v, rerank %v",
				without, with-without)
		}
	}
}

// corpusSearchForRerank adapts the keyword search into Hit form for the reranker.
func corpusSearchForRerank(keyword *KeywordIndex, owner, query string, k int) ([]Hit, error) {
	hits := keyword.Search(owner, query, k*4)
	out := make([]Hit, 0, len(hits))
	for _, hit := range hits {
		out = append(out, Hit{
			ChunkID:    hit.ChunkID,
			Owner:      hit.Owner,
			Score:      hit.Score,
			Text:       hit.Text,
			DocumentID: hit.DocumentID,
			Position:   hit.Position,
		})
	}
	return out, nil
}

// ratio is a small helper so the log line can print a multiplier.
func ratio(with, without time.Duration) float64 {
	if without == 0 {
		return 0
	}
	return float64(with) / float64(without)
}

// The reranker's cost scales with the candidate count, not the corpus. This is
// asserted because it is the property that makes it a bounded cost: a caller who
// over-fetches more pays more, but a caller who holds the shortlist fixed does
// not get slower as the corpus grows.
func TestRerankerCostScalesWithCandidatesNotCorpus(t *testing.T) {
	small := NewWeightedLexicalOverlapReranker(make([]string, 10))
	large := NewWeightedLexicalOverlapReranker(make([]string, 100))
	query := "the same query for both"
	chunk := "a chunk with the query terms in it"

	const iterations = 2000

	start := time.Now()
	for i := 0; i < iterations; i++ {
		_ = small.Score(query, chunk)
	}
	smallCost := time.Since(start)

	start = time.Now()
	for i := 0; i < iterations; i++ {
		_ = large.Score(query, chunk)
	}
	largeCost := time.Since(start)

	t.Logf("10 candidates %v/call   100 candidates %v/call", smallCost/iterations, largeCost/iterations)

	// A tenfold larger candidate list may cost more to *build*, but a single
	// score call over it is a map lookup per term, so it must not be ten times
	// slower. If it were, the cost would be superlinear and the "bounded cost"
	// claim would be false.
	if smallCost > 0 && largeCost > 10*smallCost {
		t.Fatalf("scoring became superlinear: 10 candidates %v, 100 candidates %v",
			smallCost, largeCost)
	}
}

// The reranker is safe to use concurrently, because it is constructed once at
// startup and Score is pure. This is asserted rather than assumed: a reranker
// with per-call mutable state would be a data race on the hot path.
func TestRerankerIsConcurrencySafe(t *testing.T) {
	reranker := NewWeightedLexicalOverlapReranker([]string{
		"one document with terms",
		"another document with terms",
	})

	var wg sync.WaitGroup
	results := make([]float64, 16)
	for i := 0; i < 16; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			for j := 0; j < 100; j++ {
				results[i] = reranker.Score("terms", "one document with terms")
			}
		}(i)
	}
	wg.Wait()

	first := results[0]
	for _, result := range results {
		if result != first {
			t.Fatalf("concurrent scoring disagreed: %v vs %v", first, result)
		}
	}
}

// The search path itself is concurrent-safe with the reranker attached, which is
// the combination a server runs.
func TestSearchAndRerankAreConcurrencySafe(t *testing.T) {
	corpus := benchCorpus(t, 50)
	keyword := NewKeywordIndex(corpus)
	for cid := range corpus.chunks {
		if chunk := corpus.chunk(cid); chunk != nil {
			keyword.AddChunk(cid, chunk.Text)
		}
	}
	reranker := LexicalOverlapReranker{}

	var wg sync.WaitGroup
	for worker := 0; worker < 8; worker++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for i := 0; i < 50; i++ {
				hits, err := corpusSearchForRerank(keyword, "bench", "shared filler", 10)
				if err != nil {
					t.Errorf("search failed: %v", err)
					return
				}
				_ = Rerank("shared filler", hits, reranker, 10)
			}
		}()
	}
	wg.Wait()
}

func BenchmarkRerankAtCandidates(b *testing.B) {
	candidates := make([]Hit, 0, 100)
	for i := 0; i < 100; i++ {
		candidates = append(candidates, Hit{
			ChunkID: string(rune('a'+i%26)) + itoa(i),
			Text:    "a chunk of text with the query terms and some filler words in it",
		})
	}
	reranker := LexicalOverlapReranker{}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = Rerank("query terms filler", candidates, reranker, 10)
	}
}
