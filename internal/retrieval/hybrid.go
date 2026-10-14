package retrieval

import "sort"

// ---------------------------------------------------------------------------
// Hybrid search
// ---------------------------------------------------------------------------

// Hybrid weights for the two retrieval paths.
//
// The vector path finds paraphrases the keyword path cannot: "how do I rotate
// a secret" matches "credential rotation procedure". The keyword path finds
// exact terms the vector path misses: an error code, a symbol, an identifier.
// Neither dominates, so the default is even and the weights are configurable
// because the right balance is a property of the corpus, not of the algorithm.
const (
	defaultVectorWeight = 1.0
	defaultKeywordWeight = 1.0

	// rrfK is the Reciprocal Rank Fusion constant. It is what makes fusing
	// two score scales possible at all: the two lists are ranked by their own
	// metric, so the scores themselves are incomparable, but the ranks are
	// not. 60 is the value from the original paper and is large enough that
	// the rank-1 result of one list cannot bury the top of the other, which
	// is the failure mode of a plain score sum.
	rrfK = 60.0
)

// HybridHit is a result from the fused ranking.
type HybridHit struct {
	ChunkID string  `json:"chunk_id"`
	Owner   string  `json:"owner"`
	Score   float32 `json:"score"`
	// VectorScore and KeywordScore are the two contributing scores, kept so a
	// result that only one path found is diagnosable rather than looking like
	// a fused agreement.
	VectorScore  float32 `json:"vector_score,omitempty"`
	KeywordScore float32 `json:"keyword_score,omitempty"`
	// FromVector and FromKeyword say which paths produced this hit. A hit from
	// only one path is the interesting case: it is what the other path missed.
	FromVector  bool `json:"from_vector"`
	FromKeyword bool `json:"from_keyword"`
	Text        string `json:"text"`
	// DocumentID and Position are the citation.
	DocumentID string `json:"document_id"`
	Position   int    `json:"position"`
}

// HybridParams configures the fused search.
type HybridParams struct {
	// VectorWeight and KeywordWeight scale each path's contribution. A zero
	// weight disables that path entirely, which is how a pure vector or pure
	// keyword search is expressed through the same entry point.
	VectorWeight  float32
	KeywordWeight float32
}

// DefaultHybridParams returns an even fusion.
func DefaultHybridParams() HybridParams {
	return HybridParams{VectorWeight: defaultVectorWeight, KeywordWeight: defaultKeywordWeight}
}

// HybridQuery runs both retrieval paths over the owner's partition and fuses
// their rankings with Reciprocal Rank Fusion.
//
// The owner is passed to both paths and never used to filter afterwards, so
// the access control is the same as for either path alone. Neither list is
// ever truncated before fusion: fusing the top-k of each would discard a
// result that ranks low on one path but first on the other, which is the
// entire reason to fuse.
func HybridQuery(ix *Index, ki *KeywordIndex, owner, query string, k int, params HybridParams) ([]HybridHit, error) {
	if k <= 0 {
		return nil, nil
	}
	if ix == nil && ki == nil {
		return nil, nil
	}
	// A query with no terms is not a query. The vector path alone would still
	// answer it, because it embeds the text - and an embedder maps whitespace
	// to the zero vector, whose cosine is 0 against everything, so the
	// candidates sort by chunk id and the caller receives a full page of
	// arbitrary results that look like matches. The keyword path returning
	// nothing is not enough; the fused result must also be empty.
	if len(Tokenize(query)) == 0 {
		return nil, nil
	}

	// Over-fetch both paths so the fusion has full rankings to work with, but
	// not unbounded: a corpus of a million chunks does not need a million
	// scored per query. The multiplier is generous because a result at rank
	// 200 in one list can still be rank 1 in the other.
	const recallFactor = 10
	fetch := k * recallFactor

	type entry struct {
		hit HybridHit
	}
	fused := map[string]*entry{}

	record := func(h HybridHit, weight float32) {
		existing := fused[h.ChunkID]
		if existing == nil {
			existing = &entry{hit: h}
			fused[h.ChunkID] = existing
		} else {
			// Merge the two paths' views of the same chunk: either may have
			// found it, and the citations agree because both come from the
			// same corpus row.
			existing.hit.FromVector = existing.hit.FromVector || h.FromVector
			existing.hit.FromKeyword = existing.hit.FromKeyword || h.FromKeyword
			if h.VectorScore != 0 {
				existing.hit.VectorScore = h.VectorScore
			}
			if h.KeywordScore != 0 {
				existing.hit.KeywordScore = h.KeywordScore
			}
		}
		existing.hit.Score += weight
	}

	if ix != nil && params.VectorWeight > 0 {
		vectorHits, err := ix.Search(owner, query, fetch)
		if err != nil {
			// A vector path that cannot run (no embedder) is not a reason to
			// fail the whole query when the keyword path can still answer.
			if err != errNoEmbedder {
				return nil, err
			}
		}
		for rank, hit := range vectorHits {
			record(HybridHit{
				ChunkID:    hit.ChunkID,
				Owner:      hit.Owner,
				VectorScore: hit.Score,
				FromVector: true,
				Text:       hit.Text,
				DocumentID: hit.DocumentID,
				Position:   hit.Position,
			}, params.VectorWeight/rrfRankScore(rank))
		}
	}

	if ki != nil && params.KeywordWeight > 0 {
		for rank, hit := range ki.Search(owner, query, fetch) {
			record(HybridHit{
				ChunkID:     hit.ChunkID,
				Owner:       hit.Owner,
				KeywordScore: hit.Score,
				FromKeyword: true,
				Text:        hit.Text,
				DocumentID:  hit.DocumentID,
				Position:    hit.Position,
			}, params.KeywordWeight/rrfRankScore(rank))
		}
	}

	out := make([]HybridHit, 0, len(fused))
	for _, e := range fused {
		out = append(out, e.hit)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Score != out[j].Score {
			return out[i].Score > out[j].Score
		}
		return out[i].ChunkID < out[j].ChunkID
	})
	if k > len(out) {
		k = len(out)
	}
	return out[:k], nil
}

// rrfRankScore converts a zero-based rank into its fusion weight. The +1 is
// why the first result contributes 1/k rather than 1/(k+60), which would make
// the rank-1 and rank-2 results nearly indistinguishable.
func rrfRankScore(rank int) float32 {
	return float32(rank) + 1 + rrfK
}
