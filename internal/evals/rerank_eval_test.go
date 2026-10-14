package evals

import (
	"math/rand"
	"testing"

	"github.com/astrovox/astrovox/internal/retrieval"
)

// The adoption decision for the reranker, made by measurement rather than by
// preference.
//
// WS-C-004 is explicit: a reranker is adopted only if it improves measured
// nDCG. So this test reports the before and after numbers and fails when the
// reranker is worse on any metric, which is the condition under which it must
// not ship. It passes when the reranker is better or equal, so the default can
// stay off until someone demonstrates a gain here.
func TestRerankerAdoptionIsMeasured(t *testing.T) {
	rng := rand.New(rand.NewSource(7))
	_, ix, ki, titles := buildLargeCorpus(rng)
	set := largeSet(titles)

	base := RetrievalAdapter{Index: ix, Keyword: ki, Params: retrieval.DefaultHybridParams()}
	before, err := Run(set, base, 5)
	if err != nil {
		t.Fatalf("baseline eval failed: %v", err)
	}

	reranked := RerankingAdapter{Inner: base, Reranker: retrieval.NewWeightedLexicalOverlapReranker(nil), Overfetch: 4}
	after, err := Run(set, reranked, 5)
	if err != nil {
		t.Fatalf("reranked eval failed: %v", err)
	}

	t.Logf("before: %s", before.String())
	t.Logf("after : %s", after.String())

	comparison := Compare(before, after)
	t.Logf("recall %+.3f  mrr %+.3f  ndcg %+.3f", comparison.RecallDelta, comparison.MRRDelta, comparison.NDCGDelta)

	// A reranker that costs recall or MRR is not an improvement, whatever it
	// does to nDCG: it is trading away the thing the user notices.
	if comparison.RecallDelta < 0 {
		t.Fatalf("reranker lost recall (%+.3f); it must not ship", comparison.RecallDelta)
	}
	if comparison.MRRDelta < 0 {
		t.Fatalf("reranker lost MRR (%+.3f); it must not ship", comparison.MRRDelta)
	}
	if comparison.MissCountAfter > comparison.MissCountBefore {
		t.Fatalf("reranker created misses (%d -> %d)", comparison.MissCountBefore, comparison.MissCountAfter)
	}
}

// The weighted reranker builds its rarity table from the candidates it scores,
// which is the only honest source for it: information from the whole corpus
// would leak index statistics into a reranker that is supposed to be scoring a
// shortlist.
func TestWeightedRerankerUsesTheCandidateList(t *testing.T) {
	reranker := retrieval.NewWeightedLexicalOverlapReranker([]string{
		"postgres credential rotation procedure",
		"postgres credential rotation procedure backup",
		"unrelated document about weather",
	})

	// "procedure" appears in every candidate, so it carries no signal; "weather"
	// appears in one, so it is rare and worth more per occurrence.
	dense := reranker.Score("procedure", "postgres credential rotation procedure")
	rare := reranker.Score("weather", "unrelated document about weather")

	if dense >= rare {
		t.Fatalf("a term in every candidate scored %.3f, not below the rare term's %.3f", dense, rare)
	}
}

func TestRerankIsDeterministic(t *testing.T) {
	// Two identical calls must return the same order, or an eval cannot tell a
	// reranker improvement from reranker noise.
	candidates := []retrieval.Hit{
		{ChunkID: "c2", Text: "alpha beta gamma"},
		{ChunkID: "c1", Text: "alpha beta"},
		{ChunkID: "c3", Text: "gamma delta"},
	}
	reranker := retrieval.LexicalOverlapReranker{}

	first := retrieval.Rerank("alpha gamma", candidates, reranker, 3)
	second := retrieval.Rerank("alpha gamma", candidates, reranker, 3)
	if len(first) != len(second) {
		t.Fatalf("length differed: %d vs %d", len(first), len(second))
	}
	for i := range first {
		if first[i].ChunkID != second[i].ChunkID {
			t.Fatalf("position %d differed: %s vs %s", i, first[i].ChunkID, second[i].ChunkID)
		}
	}
}

func TestRerankPromotesAChunkTheFirstPassRankedLow(t *testing.T) {
	// The whole reason to rerank: a chunk ranked low that matches the query
	// exactly must be able to reach the top.
	candidates := []retrieval.Hit{
		{ChunkID: "no-match", Text: "nothing here resembles the question at all"},
		{ChunkID: "exact", Text: "the exact answer is in this chunk"},
	}
	reranked := retrieval.Rerank("exact answer", candidates, retrieval.LexicalOverlapReranker{}, 2)

	if len(reranked) == 0 || reranked[0].ChunkID != "exact" {
		t.Fatalf("the matching chunk was not promoted: %v", reranked)
	}
}

func TestRerankWithNilRerankerLeavesTheOrderAlone(t *testing.T) {
	candidates := []retrieval.Hit{
		{ChunkID: "c1", Score: 0.9},
		{ChunkID: "c2", Score: 0.5},
	}
	out := retrieval.Rerank("anything", candidates, nil, 5)
	if len(out) != 2 || out[0].ChunkID != "c1" {
		t.Fatalf("nil reranker changed the order: %v", out)
	}
}

func TestRerankWithZeroKReturnsTheCandidates(t *testing.T) {
	candidates := []retrieval.Hit{{ChunkID: "c1"}}
	if out := retrieval.Rerank("q", candidates, retrieval.LexicalOverlapReranker{}, 0); len(out) != 1 {
		t.Fatalf("k=0 returned %d candidates", len(out))
	}
}

func TestRerankOverfetchIsNeededToPromote(t *testing.T) {
	// A reranker given only the final k cannot promote anything it was never
	// shown. This is why the adapter over-fetches: the reranker is useless if
	// the shortlist is cut to the cutoff before it runs.
	rng := rand.New(rand.NewSource(7))
	_, ix, ki, titles := buildLargeCorpus(rng)
	set := largeSet(titles)

	base := RetrievalAdapter{Index: ix, Keyword: ki, Params: retrieval.DefaultHybridParams()}
	tight := RerankingAdapter{Inner: base, Reranker: retrieval.LexicalOverlapReranker{}, Overfetch: 1}
	wide := RerankingAdapter{Inner: base, Reranker: retrieval.LexicalOverlapReranker{}, Overfetch: 4}

	tightReport, err := Run(set, tight, 5)
	if err != nil {
		t.Fatalf("tight eval failed: %v", err)
	}
	wideReport, err := Run(set, wide, 5)
	if err != nil {
		t.Fatalf("wide eval failed: %v", err)
	}

	t.Logf("overfetch=1: %s", tightReport.String())
	t.Logf("overfetch=4: %s", wideReport.String())

	if wideReport.MeanRecallAtK < tightReport.MeanRecallAtK {
		t.Fatalf("over-fetching made recall worse (%.3f < %.3f), which should be impossible",
			wideReport.MeanRecallAtK, tightReport.MeanRecallAtK)
	}
}
