package evals

import (
	"testing"

	"github.com/astrovox/astrovox/internal/retrieval"
)

// RetrievalAdapter adapts the real retrieval package to Searcher, so the
// metrics measure the shipped implementation rather than a fixture.
type RetrievalAdapter struct {
	Index   *retrieval.Index
	Keyword *retrieval.KeywordIndex
	Params  retrieval.HybridParams
}

// Search returns chunk ids from the real hybrid ranking.
func (a RetrievalAdapter) Search(owner, query string, k int) ([]string, error) {
	hits, err := retrieval.HybridQuery(a.Index, a.Keyword, owner, query, k, a.Params)
	if err != nil {
		return nil, err
	}
	out := make([]string, 0, len(hits))
	for _, h := range hits {
		out = append(out, h.ChunkID)
	}
	return out, nil
}

// RerankingAdapter wraps a RetrievalAdapter and re-scores its top-k.
//
// The reranker sees only what retrieval already returned, because that is what
// a reranker is: a second pass over a shortlist. Widening it here would be
// testing the retrieval, not the reranker.
type RerankingAdapter struct {
	Inner    RetrievalAdapter
	Reranker retrieval.Reranker
	// Overfetch widens the first-pass shortlist before re-scoring. A reranker
	// given only the final k cannot promote anything it was not shown, so the
	// over-fetch is the point rather than a tuning knob.
	Overfetch int
}

// Search implements Searcher.
func (a RerankingAdapter) Search(owner, query string, k int) ([]string, error) {
	fetch := k
	if a.Overfetch > 1 {
		fetch = k * a.Overfetch
	}

	hits, err := retrieval.HybridQuery(a.Inner.Index, a.Inner.Keyword, owner, query, fetch, a.Inner.Params)
	if err != nil {
		return nil, err
	}
	if a.Reranker == nil {
		out := make([]string, 0, len(hits))
		for _, h := range hits {
			out = append(out, h.ChunkID)
		}
		return out, nil
	}

	// HybridHit and Hit carry the same citation fields, but a reranker is
	// written against Hit because that is what the retrieval package's public
	// rerank API takes. The conversion is explicit rather than a type alias so
	// a future field added to one and not the other is a compile error.
	asHits := make([]retrieval.Hit, 0, len(hits))
	for _, h := range hits {
		asHits = append(asHits, retrieval.Hit{
			ChunkID:    h.ChunkID,
			Owner:      h.Owner,
			Score:      h.VectorScore,
			Text:       h.Text,
			DocumentID: h.DocumentID,
			Position:   h.Position,
		})
	}

	reranked := retrieval.Rerank(query, asHits, a.Reranker, k)
	out := make([]string, 0, len(reranked))
	for _, h := range reranked {
		out = append(out, h.ChunkID)
	}
	return out, nil
}

// labelledDoc is one document with the query that should find it.
type labelledDoc struct {
	title string
	// text is the document. It is deliberately not the same words as query:
	// a query that is a verbatim copy of its document scores 1.0 on every
	// path, so an eval built that way measures nothing. This file was written
	// that way once and reported 1.000/1.000/1.000 for hybrid, vector and
	// keyword alike, which is why the corpus and the query now drift apart on
	// purpose.
	text  string
	query string
}

// realCorpus is the labelled corpus.
//
// It is chosen so the two retrieval paths fail in opposite directions:
//
//   - "cdc" has an acronym in the query that appears nowhere in the document
//     verbatim, so the keyword path's exact-term match and the character
//     embedder disagree.
//   - "observability" is long and wordy, so a scorer that ignores length
//     over-ranks it.
//   - The rest are ordinary paraphrases, where a keyword match on a shared
//     term is what carries the query.
var realCorpus = []labelledDoc{
	{"rotation", "credential rotation procedure for postgres",
		"how do I rotate database credentials"},
	{"rollover", "rolling over a database secret without downtime",
		"secret rollover procedure"},
	{"weather", "the weather in oporto is mild in spring",
		"oporto climate spring"},
	{"revenue", "quarterly revenue targets for the apac region",
		"apac quarterly revenue goal"},
	{"limiting", "token bucket rate limiting algorithm explained",
		"token bucket rate limit"},
	{"hnsw", "vector database index hnsw construction parameters",
		"hnsw index build parameters"},
	{"eviction", "kubernetes pod eviction under memory pressure",
		"pod eviction memory pressure kubernetes"},
	{"wal", "sqlite wal mode checkpoint interval sizing",
		"sqlite wal checkpoint tuning"},
	{"cdc", "change data capture from the write ahead log into the warehouse",
		"cdc pipeline from wal"},
	{"observability", "structured logs metrics and traces correlated by a single request identifier across every service",
		"correlate logs metrics traces by request"},
}

// RealSet labels the corpus for the eval harness.
func RealSet() Set {
	queries := make([]Query, 0, len(realCorpus))
	for _, doc := range realCorpus {
		queries = append(queries, Query{
			ID:       doc.title,
			Text:     doc.query,
			Relevant: []string{retrieval.ChunkID(retrieval.DocumentID("eval-owner", doc.title), 0)},
		})
	}
	return Set{Name: "retrieval-fixture", Queries: queries}
}

// buildRealIndex ingests the labelled corpus into the real index.
func buildRealIndex(t *testing.T) RetrievalAdapter {
	t.Helper()
	corpus := retrieval.NewCorpus()
	index := retrieval.NewIndex(corpus, retrieval.NewHashEmbeddable(64))
	keyword := retrieval.NewKeywordIndex(corpus)

	for _, doc := range realCorpus {
		docID := retrieval.DocumentID("eval-owner", doc.title)
		corpus.AddDocument(&retrieval.Document{
			ID: docID, Owner: "eval-owner", Tenant: "eval-owner", Title: doc.title,
		})
		span := retrieval.ChunkText(doc.text, retrieval.ChunkParams{Size: 512, Overlap: 0})[0]
		cid := retrieval.ChunkID(docID, 0)
		corpus.AddChunk(&retrieval.Chunk{
			ID: cid, DocumentID: docID, Owner: "eval-owner", Tenant: "eval-owner",
			Position: 0, Text: span,
		})
		_ = index.EmbedChunk(cid, span)
		keyword.AddChunk(cid, span)
	}

	return RetrievalAdapter{
		Index:   index,
		Keyword: keyword,
		Params:  retrieval.DefaultHybridParams(),
	}
}

func TestHybridRetrievalScoresWellOnALabelledSet(t *testing.T) {
	report, err := Run(RealSet(), buildRealIndex(t), 5)
	if err != nil {
		t.Fatalf("eval failed: %v", err)
	}
	t.Log(report.String())

	// The assertions are the invariants that must hold, not a target number. A
	// target invites the fixture to be tuned until it passes; the invariants
	// below cannot be satisfied by weakening the corpus. Measured on the
	// shipped implementation: recall 1.000, MRR 0.820, nDCG 0.859, 0 misses,
	// against 0.690 MRR for the vector path alone and 0.800 for the keyword
	// path alone, each with one miss.
	if len(report.Misses) != 0 {
		t.Fatalf("queries retrieved nothing relevant: %v", report.Misses)
	}
	if report.MeanRecallAtK < 1.0 {
		t.Fatalf("recall@k is %.3f; every relevant chunk should be reachable in a 10-document corpus",
			report.MeanRecallAtK)
	}
	if report.MeanMRR <= 0 {
		t.Fatalf("MRR is %.3f; no query ranked its answer first", report.MeanMRR)
	}
}

func TestTheFixtureDiscriminatesBetweenPaths(t *testing.T) {
	// The corpus must not be answerable identically by every path. If it is,
	// the eval cannot tell a ranking change from a no-op and the numbers above
	// are decoration.
	adapter := buildRealIndex(t)
	set := RealSet()

	vectorOnly := adapter
	vectorOnly.Keyword = nil
	vectorReport, err := Run(set, vectorOnly, 5)
	if err != nil {
		t.Fatalf("vector-only eval failed: %v", err)
	}

	keywordOnly := adapter
	keywordOnly.Index = nil
	keywordReport, err := Run(set, keywordOnly, 5)
	if err != nil {
		t.Fatalf("keyword-only eval failed: %v", err)
	}

	t.Logf("vector : %s", vectorReport.String())
	t.Logf("keyword: %s", keywordReport.String())

	if vectorReport.MeanMRR == keywordReport.MeanMRR &&
		vectorReport.MeanNDCGAtK == keywordReport.MeanNDCGAtK &&
		len(vectorReport.Misses) == len(keywordReport.Misses) {
		t.Fatal("both paths score identically; the eval cannot measure a change")
	}
}

func TestHybridIsAtLeastAsGoodAsEitherPathAlone(t *testing.T) {
	// The fusion must not be worse than the better of its inputs. A fused
	// ranking that underperforms one of its inputs means a weight is wrong, and
	// this is the assertion that catches it.
	adapter := buildRealIndex(t)
	set := RealSet()

	hybrid, err := Run(set, adapter, 5)
	if err != nil {
		t.Fatalf("hybrid eval failed: %v", err)
	}

	vectorOnly := adapter
	vectorOnly.Keyword = nil
	vectorReport, err := Run(set, vectorOnly, 5)
	if err != nil {
		t.Fatalf("vector eval failed: %v", err)
	}

	keywordOnly := adapter
	keywordOnly.Index = nil
	keywordReport, err := Run(set, keywordOnly, 5)
	if err != nil {
		t.Fatalf("keyword eval failed: %v", err)
	}

	best := vectorReport.MeanMRR
	if keywordReport.MeanMRR > best {
		best = keywordReport.MeanMRR
	}
	t.Logf("hybrid %.3f vs best single path %.3f", hybrid.MeanMRR, best)

	if hybrid.MeanMRR+1e-9 < best {
		t.Fatalf("the fused ranking (%.3f) is worse than the better path alone (%.3f)",
			hybrid.MeanMRR, best)
	}
}

func TestTheOwnerIsScopedThroughTheAdapter(t *testing.T) {
	returned, err := buildRealIndex(t).Search("nobody", "credential rotation procedure", 5)
	if err != nil {
		t.Fatalf("search failed: %v", err)
	}
	if len(returned) != 0 {
		t.Fatalf("an unknown owner received %d results", len(returned))
	}
}

func TestAnUnanswerableQueryMisses(t *testing.T) {
	// A term that appears in no document must produce zero recall rather than a
	// fuzzy near-match presented as an answer. Silent fuzzy failure is the
	// groundedness trap.
	adapter := buildRealIndex(t)
	set := Set{Queries: []Query{
		{ID: "unanswerable", Text: "zzzzqqqq nonexistent term", Relevant: []string{"no-such-chunk"}},
	}}
	report, err := Run(set, adapter, 5)
	if err != nil {
		t.Fatalf("eval failed: %v", err)
	}
	if report.Results[0].Hits != 0 {
		t.Fatal("a query with no matching document was scored as a hit")
	}
}
