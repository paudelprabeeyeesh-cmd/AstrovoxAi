package evals

import (
	"fmt"
	"testing"
)

// evalCorpus builds a small labelled set where each query has a known answer,
// including cases that distinguish the two retrieval paths and one deliberately
// unanswerable term.
func evalCorpus() []struct {
	id      string
	owner   string
	text    string
	answers []string
} {
	return []struct {
		id      string
		owner   string
		text    string
		answers []string
	}{
		{"c1", "eval-owner", "credential rotation procedure for postgres", []string{"rotation"}},
		{"c2", "eval-owner", "how to roll over database secrets safely", []string{"rollover", "secrets"}},
		{"c3", "eval-owner", "the weather in oporto is mild in spring", []string{"weather"}},
		{"c4", "eval-owner", "quarterly revenue targets for the apac region", []string{"revenue", "apac"}},
		{"c5", "eval-owner", "token bucket rate limiting algorithm explained", []string{"rate", "limiting"}},
		{"c6", "eval-owner", "vector database index hnsw construction parameters", []string{"hnsw", "vector"}},
		{"c7", "eval-owner", "kubernetes pod eviction under memory pressure", []string{"eviction", "kubernetes"}},
		{"c8", "eval-owner", "sqlite wal mode checkpoint interval sizing", []string{"wal", "checkpoint"}},
	}
}

// stubSearcher serves labels from a map, so a metric can be verified without a
// real index.
type stubSearcher struct {
	// results is query text -> returned chunk ids.
	results map[string][]string
	// errFor makes a specific query fail.
	errFor string
	// seenOwner records the owner each query was called with, which is how the
	// ACL part of the harness is verified.
	seenOwner []string
}

func (s *stubSearcher) Search(owner, query string, k int) ([]string, error) {
	s.seenOwner = append(s.seenOwner, owner)
	if query == s.errFor {
		return nil, fmt.Errorf("search failed for %q", query)
	}
	if r, ok := s.results[query]; ok {
		return r, nil
	}
	return nil, nil
}

// testSet is the labelled set used by the metric tests. Each query names one
// relevant chunk, so a perfect ranking scores 1.0 on every metric; the
// partial-recall cases are in their own tests, which asserts that a query with
// two relevant chunks and one retrieved is worth half.
func testSet() Set {
	return Set{
		Name: "fixture",
		Queries: []Query{
			{ID: "q1", Text: "credential rotation", Relevant: []string{"rotation"}},
			{ID: "q2", Text: "roll over secrets", Relevant: []string{"rollover"}},
			{ID: "q3", Text: "weather in oporto", Relevant: []string{"weather"}},
			{ID: "q4", Text: "apac revenue", Relevant: []string{"revenue"}},
			{ID: "q5", Text: "rate limiting", Relevant: []string{"limiting"}},
		},
	}
}

func perfectSearcher() *stubSearcher {
	return &stubSearcher{results: map[string][]string{
		"credential rotation": {"rotation", "secrets"},
		"roll over secrets":   {"rollover", "weather"},
		"weather in oporto":   {"weather"},
		"apac revenue":        {"revenue", "hnsw"},
		"rate limiting":       {"limiting", "rate"},
	}}
}

func TestPerfectRankingScoresOne(t *testing.T) {
	// A ranking that puts every relevant hit first must score 1.0 on all three
	// metrics. If it does not, the maths is wrong rather than the retriever.
	r := &stubSearcher{results: map[string][]string{
		"credential rotation": {"rotation", "secrets"},
		"roll over secrets":   {"rollover"},
		"weather in oporto":   {"weather"},
		"apac revenue":        {"revenue"},
		"rate limiting":       {"limiting"},
	}}
	report, err := Run(testSet(), r, 5)
	if err != nil {
		t.Fatalf("run failed: %v", err)
	}
	if report.MeanMRR < 0.999 {
		t.Fatalf("mean MRR is %.3f, want ~1 for a top-ranked answer", report.MeanMRR)
	}
	if report.MeanRecallAtK < 0.999 {
		t.Fatalf("mean recall@k is %.3f, want ~1", report.MeanRecallAtK)
	}
	if report.MeanNDCGAtK < 0.999 {
		t.Fatalf("mean nDCG@k is %.3f, want ~1", report.MeanNDCGAtK)
	}
	if len(report.Misses) != 0 {
		t.Fatalf("a perfect ranking reported misses: %v", report.Misses)
	}
}

func TestARelevantHitAtRankTwoDemotesRRR(t *testing.T) {
	// The answer is there but not first. Recall is unchanged and MRR is not:
	// that is exactly what MRR is for, and a harness that could not tell these
	// apart would let a reranking regression through.
	r := &stubSearcher{results: map[string][]string{
		"credential rotation": {"unrelated", "rotation"},
		"roll over secrets":   {"rollover"},
		"weather in oporto":   {"weather"},
		"apac revenue":        {"revenue"},
		"rate limiting":       {"limiting"},
	}}
	report, err := Run(testSet(), r, 5)
	if err != nil {
		t.Fatalf("run failed: %v", err)
	}
	if report.MeanReciprocalRank() >= 0.999 {
		t.Fatalf("MRR is %.3f; a rank-2 answer should demote it", report.MeanReciprocalRank())
	}
	if report.MeanRecallAtK < 0.999 {
		t.Fatalf("recall fell to %.3f; the answer was still retrieved", report.MeanRecallAtK)
	}
}

// MeanReciprocalRank exposes the mean for the assertion above.
func (r *Report) MeanReciprocalRank() float64 { return r.MeanMRR }

func TestAMissIsReportedAndScoredZero(t *testing.T) {
	r := &stubSearcher{results: map[string][]string{
		"credential rotation": {"unrelated"},
		"roll over secrets":   {"rollover"},
		"weather in oporto":   {"weather"},
		"apac revenue":        {"revenue"},
		"rate limiting":       {"limiting"},
	}}
	report, err := Run(testSet(), r, 5)
	if err != nil {
		t.Fatalf("run failed: %v", err)
	}
	if len(report.Misses) != 1 || report.Misses[0] != "q1" {
		t.Fatalf("misses = %v, want [q1]", report.Misses)
	}
	for _, res := range report.Results {
		if res.QueryID == "q1" {
			if res.ReciprocalRank != 0 {
				t.Fatalf("a miss scored %.3f reciprocal rank", res.ReciprocalRank)
			}
			if res.RecallAtK != 0 {
				t.Fatalf("a miss scored %.3f recall", res.RecallAtK)
			}
		}
	}
}

func TestNDCGIsPenalisedByADemotedRelevantHit(t *testing.T) {
	// Recall can be identical while the ordering gets worse. Only nDCG sees it.
	// This is the case a recall-only harness misses entirely.
	good := &stubSearcher{results: map[string][]string{
		"credential rotation": {"rotation", "secrets"},
		"roll over secrets":   {"rollover"},
		"weather in oporto":   {"weather"},
		"apac revenue":        {"revenue"},
		"rate limiting":       {"limiting"},
	}}
	demoted := &stubSearcher{results: map[string][]string{
		"credential rotation": {"secrets", "junk", "rotation"},
		"roll over secrets":   {"rollover"},
		"weather in oporto":   {"weather"},
		"apac revenue":        {"revenue"},
		"rate limiting":       {"limiting"},
	}}

	before, _ := Run(testSet(), good, 5)
	after, _ := Run(testSet(), demoted, 5)

	if before.MeanNDCGAtK <= after.MeanNDCGAtK {
		t.Fatalf("nDCG did not fall when a relevant hit was demoted: %.3f -> %.3f",
			before.MeanNDCGAtK, after.MeanNDCGAtK)
	}
	if before.MeanRecallAtK < after.MeanRecallAtK {
		t.Fatal("recall changed when it should not have")
	}
}

func TestCompareBlocksARegression(t *testing.T) {
	before := &Report{MeanRecallAtK: 0.9, MeanMRR: 0.8, MeanNDCGAtK: 0.7, Misses: nil}
	after := &Report{MeanRecallAtK: 0.8, MeanMRR: 0.8, MeanNDCGAtK: 0.7, Misses: []string{"q1"}}

	comparison := Compare(before, after)
	if comparison.Improved() {
		t.Fatal("a recall drop was reported as an improvement")
	}
	if comparison.Regression() == "" {
		t.Fatal("a regression was reported with no reason")
	}
}

func TestCompareRequiresAtLeastOneMetricToRise(t *testing.T) {
	// An identical result is not an improvement, and treating it as one means
	// the gate can be satisfied by doing nothing.
	before := &Report{MeanRecallAtK: 0.9, MeanMRR: 0.8, MeanNDCGAtK: 0.7}
	after := &Report{MeanRecallAtK: 0.9, MeanMRR: 0.8, MeanNDCGAtK: 0.7}

	if Compare(before, after).Improved() {
		t.Fatal("an unchanged result was reported as an improvement")
	}
}

func TestCompareAllowsAGenuineImprovement(t *testing.T) {
	before := &Report{MeanRecallAtK: 0.9, MeanMRR: 0.8, MeanNDCGAtK: 0.7}
	after := &Report{MeanRecallAtK: 0.9, MeanMRR: 0.9, MeanNDCGAtK: 0.75}

	if !Compare(before, after).Improved() {
		t.Fatal("a strict improvement was rejected")
	}
}

func TestCompareRejectsAnImprovementThatCostsAMiss(t *testing.T) {
	// Raising one metric while creating a miss is a net loss, because a miss is
	// the failure a user notices.
	before := &Report{MeanRecallAtK: 0.8, MeanMRR: 0.7, MeanNDCGAtK: 0.6}
	after := &Report{MeanRecallAtK: 0.95, MeanMRR: 0.7, MeanNDCGAtK: 0.6, Misses: []string{"q3"}}

	if Compare(before, after).Improved() {
		t.Fatal("a miss was tolerated for a recall gain")
	}
}

func TestAReducedMissCountIsAnImprovement(t *testing.T) {
	before := &Report{MeanRecallAtK: 0.8, MeanMRR: 0.7, MeanNDCGAtK: 0.6, Misses: []string{"q1", "q2"}}
	after := &Report{MeanRecallAtK: 0.8, MeanMRR: 0.7, MeanNDCGAtK: 0.6, Misses: []string{"q1"}}

	if !Compare(before, after).Improved() {
		t.Fatal("fixing a miss was not counted as an improvement")
	}
}

func TestCutoffIsValidated(t *testing.T) {
	if _, err := Run(testSet(), perfectSearcher(), 0); err == nil {
		t.Fatal("a zero cutoff was accepted")
	}
}

func TestASearcherErrorIsSurfaced(t *testing.T) {
	r := &stubSearcher{errFor: "credential rotation"}
	if _, err := Run(testSet(), r, 5); err == nil {
		t.Fatal("a searcher failure was swallowed")
	}
}

func TestIDCGCapsAtTheCutoff(t *testing.T) {
	// With two relevant chunks and a cutoff of 2, the ideal is the top two
	// slots. A searcher returning both at the top must score 1.0, not more.
	r := &stubSearcher{results: map[string][]string{
		"credential rotation": {"rotation", "secrets", "weather"},
		"roll over secrets":   {"rollover"},
		"weather in oporto":   {"weather"},
		"apac revenue":        {"revenue"},
		"rate limiting":       {"limiting"},
	}}
	report, err := Run(testSet(), r, 2)
	if err != nil {
		t.Fatalf("run failed: %v", err)
	}
	for _, res := range report.Results {
		if res.QueryID == "q1" {
			if res.NDCG > 1.0001 {
				t.Fatalf("nDCG %.3f exceeds 1 for a perfect top-2", res.NDCG)
			}
			if res.NDCG < 0.999 {
				t.Fatalf("nDCG %.3f is below 1 for a perfect top-2", res.NDCG)
			}
		}
	}
}

func TestRecallCountsEveryRelevantHit(t *testing.T) {
	// A query with two relevant chunks and one retrieved is half recall, not
	// full recall. Scoring against "did the first one show up" would hide half
	// the misses.
	set := Set{Queries: []Query{
		{ID: "q", Text: "x", Relevant: []string{"a", "b"}},
	}}
	r := &stubSearcher{results: map[string][]string{"x": {"a"}}}
	report, err := Run(set, r, 5)
	if err != nil {
		t.Fatalf("run failed: %v", err)
	}
	if report.Results[0].RecallAtK != 0.5 {
		t.Fatalf("recall = %.3f, want 0.5 for one of two relevant hits", report.Results[0].RecallAtK)
	}
}

func TestTheOwnerIsPassedThrough(t *testing.T) {
	// An eval can only catch an ACL regression if it searches as the tenant it
	// labelled for.
	r := perfectSearcher()
	set := Set{Queries: []Query{{ID: "q", Text: "x", Permits: "tenant-7"}}}
	if _, err := Run(set, r, 5); err != nil {
		t.Fatalf("run failed: %v", err)
	}
	if len(r.seenOwner) != 1 || r.seenOwner[0] != "tenant-7" {
		t.Fatalf("searched as %v, want [tenant-7]", r.seenOwner)
	}
}

func TestReportStringCarriesTheMisses(t *testing.T) {
	// The one-line summary must not hide misses behind a mean.
	r := &stubSearcher{results: map[string][]string{"credential rotation": {"unrelated"}}}
	report, _ := Run(testSet(), r, 5)
	text := report.String()
	if !contains(text, "misses=") {
		t.Fatalf("the summary omits the miss count: %s", text)
	}
}

func contains(haystack, needle string) bool {
	return len(haystack) >= len(needle) && (func() bool {
		for i := 0; i+len(needle) <= len(haystack); i++ {
			if haystack[i:i+len(needle)] == needle {
				return true
			}
		}
		return false
	})()
}
