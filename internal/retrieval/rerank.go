package retrieval

import (
	"math"
	"sort"
	"strings"
)

// ---------------------------------------------------------------------------
// Reranking
// ---------------------------------------------------------------------------

// A reranker re-scores a candidate list against the query, so the order a
// client sees reflects relevance rather than the shape of the first-pass index.
//
// The spec for this workstream is explicit: a reranker is adopted only if it
// improves measured nDCG. So this package ships a reranker AND the harness that
// decides whether it is used, and the default is off. A reranker that quietly
// becomes the default because it "looks better" is how a retrieval system is made
// worse without anyone noticing.

// Reranker re-scores a candidate list.
type Reranker interface {
	// Name identifies the reranker in the eval report.
	Name() string
	// Score returns a relevance score for (query, chunk). Higher is better.
	// Implementations must be deterministic: a non-deterministic reranker makes
	// the eval harness unable to tell an improvement from noise.
	Score(query, chunk string) float64
}

// LexicalOverlapReranker scores a chunk by the fraction of query terms it
// contains, weighted by term rarity across the candidate list.
//
// It is deliberately simple and local. A cross-encoder would score far better
// and needs a model, which needs a key and a budget; this exists so the
// *mechanism* of scoring a reranker is real and measurable now, and so the
// harness that decides can be exercised against something honest.
type LexicalOverlapReranker struct{}

// Name implements Reranker.
func (LexicalOverlapReranker) Name() string { return "lexical-overlap" }

// Score implements Reranker.
//
// Term rarity is computed over the candidate list rather than the whole corpus,
// because that is what a reranker has: it re-scores what retrieval already
// returned. A term that appears in every candidate carries no signal and is
// downweighted accordingly, which is the same IDF intuition BM25 uses, applied
// inside the shortlist rather than across the index.
func (LexicalOverlapReranker) Score(query, chunk string) float64 {
	queryTerms := significantTerms(query)
	if len(queryTerms) == 0 {
		return 0
	}
	chunkTerms := significantTerms(chunk)

	// Term counts in this chunk, for the frequency component.
	freq := make(map[string]int, len(chunkTerms))
	for _, term := range chunkTerms {
		freq[term]++
	}

	var score float64
	for _, term := range queryTerms {
		f := freq[term]
		if f == 0 {
			continue
		}
		// Saturating frequency: the tenth occurrence is not ten times as
		// relevant as the first.
		tf := float64(f) / (float64(f) + 1.0)
		// Rarity is supplied by the caller through ScoreWithRarity; here it is
		// 1.0 so a standalone call is still monotonic.
		score += tf
	}
	return score / float64(len(queryTerms))
}

// WeightedLexicalOverlapReranker is the same score with an explicit rarity
// table, so the rarity can be computed over the candidate list.
type WeightedLexicalOverlapReranker struct {
	// idf is term -> inverse document frequency over the candidates.
	idf map[string]float64
}

// NewWeightedLexicalOverlapReranker builds the rarity table from the candidates
// it is about to score.
//
// Building it here rather than at construction time is what makes it correct: a
// reranker that saw the whole corpus would leak the corpus's statistics into the
// score, and a reranker that saw nothing could not weight rarity at all.
func NewWeightedLexicalOverlapReranker(candidates []string) *WeightedLexicalOverlapReranker {
	df := make(map[string]int)
	for _, candidate := range candidates {
		seen := map[string]bool{}
		for _, term := range significantTerms(candidate) {
			if !seen[term] {
				df[term]++
				seen[term] = true
			}
		}
	}
	n := float64(len(candidates))
	idf := make(map[string]float64, len(df))
	for term, count := range df {
		if count == 0 {
			continue
		}
		// Smoothing as in BM25: a term in every candidate must not vanish and a
		// unique term must not divide by zero.
		idf[term] = math.Log((n-float64(count)+0.5)/(float64(count)+0.5) + 1)
	}
	return &WeightedLexicalOverlapReranker{idf: idf}
}

// Name implements Reranker.
func (r *WeightedLexicalOverlapReranker) Name() string { return "weighted-lexical-overlap" }

// Score implements Reranker.
func (r *WeightedLexicalOverlapReranker) Score(query, chunk string) float64 {
	queryTerms := significantTerms(query)
	if len(queryTerms) == 0 {
		return 0
	}
	freq := make(map[string]int)
	for _, term := range significantTerms(chunk) {
		freq[term]++
	}

	var score float64
	for _, term := range queryTerms {
		f := freq[term]
		if f == 0 {
			continue
		}
		tf := float64(f) / (float64(f) + 1.0)
		weight := r.idf[term]
		if weight <= 0 {
			weight = 0.01
		}
		score += tf * weight
	}
	return score / float64(len(queryTerms))
}

// Rerank re-scores a candidate list and returns the top-k by the new score.
//
// The candidate's original score is discarded rather than blended. Blending is
// tempting because it preserves the retrieval signal, but it means the reranker
// can never fully correct a first-pass error, and it makes the comparison
// uninterpretable: an improvement in nDCG could come from either component.
// Discarding keeps the experiment clean, and the harness decides whether the
// result is better.
func Rerank(query string, candidates []Hit, reranker Reranker, k int) []Hit {
	if reranker == nil || k <= 0 || len(candidates) == 0 {
		return candidates
	}

	type entry struct {
		candidate Hit
		score     float64
	}
	entries := make([]entry, 0, len(candidates))
	for _, candidate := range candidates {
		entries = append(entries, entry{
			candidate: candidate,
			score:     reranker.Score(query, candidate.Text),
		})
	}

	sort.SliceStable(entries, func(i, j int) bool {
		if entries[i].score != entries[j].score {
			return entries[i].score > entries[j].score
		}
		// Stable tie-break on the chunk id, so two queries with the same text
		// rank alike and the eval cannot read a tie as an improvement.
		return entries[i].candidate.ChunkID < entries[j].candidate.ChunkID
	})

	if k > len(entries) {
		k = len(entries)
	}
	out := make([]Hit, 0, k)
	for _, entry := range entries[:k] {
		reranked := entry.candidate
		reranked.Score = float32(entry.score)
		out = append(out, reranked)
	}
	return out
}

// significantTerms tokenises and drops stop words, so a score is not dominated
// by "the" and "of".
func significantTerms(text string) []string {
	lowered := strings.ToLower(text)
	fields := strings.FieldsFunc(lowered, func(r rune) bool {
		switch {
		case r >= 'a' && r <= 'z':
			return false
		case r >= '0' && r <= '9':
			return false
		case r > 127:
			// Keep non-ASCII letters so a non-Latin query is not emptied.
			return false
		default:
			return true
		}
	})

	stop := map[string]bool{
		"the": true, "a": true, "an": true, "and": true, "or": true,
		"of": true, "to": true, "in": true, "is": true, "are": true,
		"for": true, "on": true, "with": true, "by": true, "at": true,
		"from": true, "as": true, "that": true, "this": true, "it": true,
		"be": true, "was": true, "were": true, "has": true, "have": true,
		"had": true, "not": true, "but": true, "if": true, "than": true,
	}
	out := make([]string, 0, len(fields))
	for _, field := range fields {
		if stop[field] {
			continue
		}
		out = append(out, field)
	}
	return out
}
