// Package evals measures retrieval quality.
//
// The reason this exists as its own package rather than more assertions in the
// retrieval tests: a unit test says a search returns the right chunk, an eval
// says how well it does across a labelled set and by how much. Only the second
// one can answer "did this change make retrieval better", and only with a
// metric that degrades when the ranking degrades - a pass/fail assertion
// cannot, because it stops caring the moment it passes.
//
// Three metrics are reported, because they answer different questions:
//
//	recall@k  - did the answer appear at all? A miss is invisible to MRR.
//	mrr       - how far down was the first right answer?
//	ndcg@k    - is the whole ordering good, not just the top one?
//
// The last one is the one that catches a reranker that demotes everything.
package evals

import (
	"fmt"
	"sort"
	"strings"
)

// Query is one labelled retrieval case.
type Query struct {
	// ID names the case in a report, so a regression can be traced to it.
	ID string `json:"id"`
	// Text is what the user asks.
	Text string `json:"text"`
	// Relevant is the set of chunk ids that answer it. A set, not one id,
	// because several chunks can be equally good and scoring against a single
	// "correct" answer discards the rest.
	Relevant []string `json:"relevant"`
	// Permits says the result must belong to this owner, which is what makes
	// an eval able to catch an ACL regression as well as a relevance one.
	Permits string `json:"permits,omitempty"`
}

// Set is a labelled retrieval corpus.
type Set struct {
	Name    string  `json:"name"`
	Queries []Query `json:"queries"`
}

// Result is one query's outcome.
type Result struct {
	QueryID  string   `json:"query_id"`
	Returned []string `json:"returned"`
	// Hits is the number of relevant chunks retrieved within the cutoff.
	Hits int `json:"hits"`
	// RelevantTotal is how many relevant chunks exist for this query.
	RelevantTotal int `json:"relevant_total"`

	// RecallAtK is Hits/RelevantTotal.
	RecallAtK float64 `json:"recall_at_k"`
	// ReciprocalRank is 1/rank of the first relevant hit, 0 if none.
	ReciprocalRank float64 `json:"reciprocal_rank"`
	// FirstRelevantRank is 1-based; 0 means nothing relevant was retrieved.
	FirstRelevantRank int `json:"first_relevant_rank"`
	// DCG, IDCG and NDCG capture the whole ordering.
	DCG  float64 `json:"dcg"`
	IDCG float64 `json:"idcg"`
	NDCG float64 `json:"ndcg_at_k"`
}

// Report is the aggregate over a set.
type Report struct {
	Set     string   `json:"set"`
	Queries int      `json:"queries"`
	Results []Result `json:"results"`

	// MeanRecallAtK, MeanMRR and MeanNDCGAtK are the headline numbers.
	MeanRecallAtK float64 `json:"mean_recall_at_k"`
	MeanMRR       float64 `json:"mean_mrr"`
	MeanNDCGAtK   float64 `json:"mean_ndcg_at_k"`

	// Misses lists the queries where nothing relevant was retrieved. A mean
	// hides them, and a miss is the failure a user actually notices.
	Misses []string `json:"misses,omitempty"`
}

// Searcher is what an eval needs: the top-k ids for a query.
type Searcher interface {
	Search(owner, query string, k int) ([]string, error)
}

// Run evaluates a searcher over a set at the given cutoff.
func Run(set Set, searcher Searcher, k int) (*Report, error) {
	if k <= 0 {
		return nil, fmt.Errorf("evals: cutoff must be positive, got %d", k)
	}
	report := &Report{Set: set.Name}

	var sumRecall, sumRR, sumNDCG float64
	for _, q := range set.Queries {
		owner := q.Permits
		if owner == "" {
			// Most sets are single-tenant; the owner only matters when the set
			// is deliberately checking scope.
			owner = "eval-owner"
		}
		returned, err := searcher.Search(owner, q.Text, k)
		if err != nil {
			return nil, fmt.Errorf("evals: query %s: %w", q.ID, err)
		}

		relevant := make(map[string]bool, len(q.Relevant))
		for _, id := range q.Relevant {
			relevant[id] = true
		}

		result := Result{QueryID: q.ID, Returned: returned, RelevantTotal: len(q.Relevant)}
		for rank, id := range returned {
			if !relevant[id] {
				continue
			}
			result.Hits++
			if result.FirstRelevantRank == 0 {
				result.FirstRelevantRank = rank + 1
				result.ReciprocalRank = 1.0 / float64(rank+1)
			}
			// Binary relevance with a discounted gain: the first relevant hit
			// is worth more than the fifth even when both are relevant, which
			// is what separates nDCG from plain recall.
			result.DCG += 1.0 / log2(float64(rank+2))
		}
		result.IDCG = idealDCG(len(q.Relevant), k)
		if result.IDCG > 0 {
			result.NDCG = result.DCG / result.IDCG
		}
		if len(q.Relevant) > 0 {
			result.RecallAtK = float64(result.Hits) / float64(len(q.Relevant))
		}

		report.Results = append(report.Results, result)
		sumRecall += result.RecallAtK
		sumRR += result.ReciprocalRank
		sumNDCG += result.NDCG
		if result.Hits == 0 {
			report.Misses = append(report.Misses, q.ID)
		}
	}

	report.Queries = len(report.Results)
	if n := float64(report.Queries); n > 0 {
		report.MeanRecallAtK = sumRecall / n
		report.MeanMRR = sumRR / n
		report.MeanNDCGAtK = sumNDCG / n
	}
	return report, nil
}

// idealDCG is the best possible discounted gain for a query with `relevant`
// relevant chunks inside a cutoff of k. It is the denominator of nDCG and must
// be computed the same way as the numerator or a set with more relevant chunks
// than k is scored against an unreachable ideal.
func idealDCG(relevant, k int) float64 {
	n := relevant
	if n > k {
		n = k
	}
	var dcg float64
	for rank := 0; rank < n; rank++ {
		dcg += 1.0 / log2(float64(rank+2))
	}
	return dcg
}

// log2 avoids a math import for one logarithm. It uses
// log(x)/log(2) with log from ln via the series used elsewhere in this
// repository.
func log2(v float64) float64 {
	return ln(v) / ln(2)
}

func ln(v float64) float64 {
	if v <= 0 {
		return 0
	}
	// Reduce to [0.7, 1.5] so the series converges quickly, then use
	// log(a*b) = log(a) + log(b) with log(e^y) = y solved by halving.
	exponent := 0
	for v >= 1.5 {
		v /= 2
		exponent++
	}
	for v < 0.7 {
		v *= 2
		exponent++
	}
	y := v - 1
	sum := 0.0
	term := y
	for i := 1; i < 40; i += 2 {
		sum += term / float64(i)
		term *= -y * y
	}
	return sum + float64(exponent)*ln2
}

const ln2 = 0.6931471805599453

// String renders a report as a one-line-per-set summary. Every metric is
// printed with the miss count, so a high mean alongside several misses is
// visible rather than averaged away.
func (r *Report) String() string {
	return fmt.Sprintf(
		"%s: n=%d recall@k=%.3f mrr=%.3f ndcg@k=%.3f misses=%d%s",
		r.Set, r.Queries, r.MeanRecallAtK, r.MeanMRR, r.MeanNDCGAtK,
		len(r.Misses),
		missDetail(r.Misses),
	)
}

func missDetail(misses []string) string {
	if len(misses) == 0 {
		return ""
	}
	shown := misses
	if len(shown) > 5 {
		shown = shown[:5]
	}
	return " [" + strings.Join(shown, " ") + "]"
}

// Compare reports two reports against each other.
//
// This is the gate: a change is an improvement only when it raises at least one
// metric without lowering another. Raising recall by making the ranking worse
// is not an improvement, and a comparison that only reports one number cannot
// see that, which is why every metric and the miss count are shown.
func Compare(before, after *Report) Comparison {
	return Comparison{
		Before:          before.String(),
		After:           after.String(),
		RecallDelta:     after.MeanRecallAtK - before.MeanRecallAtK,
		MRRDelta:        after.MeanMRR - before.MeanMRR,
		NDCGDelta:       after.MeanNDCGAtK - before.MeanNDCGAtK,
		MissCountBefore: len(before.Misses),
		MissCountAfter:  len(after.Misses),
	}
}

// Comparison is the diff between two eval runs.
type Comparison struct {
	Before string `json:"before"`
	After  string `json:"after"`

	RecallDelta float64 `json:"recall_delta"`
	MRRDelta    float64 `json:"mrr_delta"`
	NDCGDelta   float64 `json:"ndcg_delta"`

	MissCountBefore int `json:"miss_count_before"`
	MissCountAfter  int `json:"miss_count_after"`
}

// Improved reports whether the later run is strictly better.
//
// Strictly is the operative word: no metric may fall, and at least one must
// rise. A run that keeps every metric identical is a regression in
// expectation, not an improvement, so it is refused.
func (c Comparison) Improved() bool {
	if c.RecallDelta < 0 || c.MRRDelta < 0 || c.NDCGDelta < 0 {
		return false
	}
	if c.MissCountAfter > c.MissCountBefore {
		return false
	}
	return c.RecallDelta > 0 || c.MRRDelta > 0 || c.NDCGDelta > 0 ||
		c.MissCountAfter < c.MissCountBefore
}

// Regression lists what got worse, so a blocked change says why.
func (c Comparison) Regression() string {
	var out []string
	if c.RecallDelta < 0 {
		out = append(out, fmt.Sprintf("recall@k %+.3f", c.RecallDelta))
	}
	if c.MRRDelta < 0 {
		out = append(out, fmt.Sprintf("mrr %+.3f", c.MRRDelta))
	}
	if c.NDCGDelta < 0 {
		out = append(out, fmt.Sprintf("ndcg@k %+.3f", c.NDCGDelta))
	}
	if c.MissCountAfter > c.MissCountBefore {
		out = append(out, fmt.Sprintf("misses %d -> %d", c.MissCountBefore, c.MissCountAfter))
	}
	sort.Strings(out)
	return strings.Join(out, ", ")
}
