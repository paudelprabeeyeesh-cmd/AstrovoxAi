package retrieval

import (
	"sort"
	"strings"
	"sync"
	"unicode"
)

// ---------------------------------------------------------------------------
// Keyword retrieval
// ---------------------------------------------------------------------------

// Tokenize splits text into index terms.
//
// Lowercasing and splitting on anything that is not a letter or a digit is
// what makes a keyword match independent of punctuation and case, which is
// most of the value of a keyword search: "PostgreSQL's" must match
// "postgres". Unicode-aware classification keeps non-Latin scripts working,
// which a bytes.IsAlnum style test silently breaks.
func Tokenize(text string) []string {
	fields := strings.FieldsFunc(text, func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsDigit(r)
	})
	out := make([]string, 0, len(fields))
	for _, f := range fields {
		out = append(out, strings.ToLower(f))
	}
	return out
}

// BM25 tuning constants.
//
// k1 saturates term frequency: the tenth occurrence of a term must not be
// worth ten times the first, because that rewards repetition over relevance.
// b controls length normalisation: at 1.0 a long document is fully penalised
// for its length, at 0.0 not at all. 0.75 is the classical choice and behaves
// well on documents of mixed length.
const (
	bm25K1 = 1.2
	bm25B  = 0.75
)

// KeywordIndex scores chunks by BM25 over their terms.
//
// It is partitioned exactly like the vector index: the postings are keyed by
// chunk id and the chunk id carries its owner, so a query can only score the
// owner's own partition. The keyword path gets the same access control as the
// vector path by construction rather than by a filter, which is the property
// the rest of this package is built around.
type KeywordIndex struct {
	mu sync.RWMutex

	corpus *Corpus

	// tf is term frequency per chunk: chunk -> term -> occurrences.
	tf map[string]map[string]int
	// postings is the inverted index: term -> chunk -> occurrences. It is the
	// same data as tf transposed, kept so a query touches only the chunks
	// containing a query term rather than every chunk in the partition.
	postings map[string]map[string]int
	// lengths is the token count per chunk, needed for length
	// normalisation.
	lengths map[string]int
	// totalLength is the sum of all lengths, so average length is a division
	// rather than a scan.
	totalLength int
}

// NewKeywordIndex returns an index over a corpus.
func NewKeywordIndex(corpus *Corpus) *KeywordIndex {
	return &KeywordIndex{
		corpus:   corpus,
		tf:       map[string]map[string]int{},
		postings: map[string]map[string]int{},
		lengths:  map[string]int{},
	}
}

// AddChunk indexes a chunk's text. It replaces any previous entry for the
// same chunk id, so re-indexing an updated chunk cannot double count its
// term frequencies.
func (ki *KeywordIndex) AddChunk(chunkID, text string) {
	terms := Tokenize(text)

	ki.mu.Lock()
	defer ki.mu.Unlock()

	// Drop the old postings before rebuilding, otherwise an updated chunk
	// keeps its stale terms in the inverted index and matches queries it no
	// longer contains.
	if old := ki.tf[chunkID]; old != nil {
		for term := range old {
			if chunks := ki.postings[term]; chunks != nil {
				delete(chunks, chunkID)
				if len(chunks) == 0 {
					delete(ki.postings, term)
				}
			}
		}
		ki.totalLength -= ki.lengths[chunkID]
	}

	if len(terms) == 0 {
		delete(ki.tf, chunkID)
		delete(ki.lengths, chunkID)
		return
	}

	freq := make(map[string]int, len(terms))
	for _, term := range terms {
		freq[term]++
	}
	ki.tf[chunkID] = freq
	ki.lengths[chunkID] = len(terms)
	ki.totalLength += len(terms)
	for term := range freq {
		if ki.postings[term] == nil {
			ki.postings[term] = map[string]int{}
		}
		ki.postings[term][chunkID] = freq[term]
	}
}

// RemoveChunk drops a chunk from the index. Called on delete so a deleted
// document stops matching queries entirely rather than lingering as a stale
// posting that would be resolved to nothing.
func (ki *KeywordIndex) RemoveChunk(chunkID string) {
	ki.mu.Lock()
	defer ki.mu.Unlock()
	for term := range ki.tf[chunkID] {
		if chunks := ki.postings[term]; chunks != nil {
			delete(chunks, chunkID)
			if len(chunks) == 0 {
				delete(ki.postings, term)
			}
		}
	}
	delete(ki.tf, chunkID)
	delete(ki.lengths, chunkID)
}

// Len returns the number of indexed chunks.
func (ki *KeywordIndex) Len() int {
	ki.mu.RLock()
	defer ki.mu.RUnlock()
	return len(ki.tf)
}

// docFrequency returns how many indexed chunks contain a term. It is the
// denominator of IDF and must be the count of *indexed* chunks, not of all
// chunks, so an empty document cannot dilute the scores.
func (ki *KeywordIndex) docFrequency(term string) int {
	return len(ki.postings[term])
}

// idf is the inverse document frequency for a term.
//
// The +1 inside the log and the +1 outside it are the standard smoothing:
// without them a term present in every document has IDF 0 and contributes
// nothing, and a term present in exactly one document divides by zero when
// df equals N.
func (ki *KeywordIndex) idf(term string, n int) float32 {
	if n == 0 {
		return 0
	}
	df := float32(ki.docFrequency(term))
	if df == 0 {
		return 0
	}
	return log32((float32(n)-df+0.5)/(df+0.5) + 1)
}

// log32 avoids a math import for one logarithm. It uses the identity
// log(x) = 2*atanh((x-1)/(x+1)), which converges quickly for the small
// positive arguments IDF produces.
func log32(v float32) float32 {
	if v <= 0 {
		return 0
	}
	y := (v - 1) / (v + 1)
	sum := float32(0)
	term := y
	y2 := y * y
	for i := 1; i < 40; i += 2 {
		sum += term / float32(i)
		term *= y2
	}
	return 2 * sum
}

// KeywordHit is a keyword search result.
type KeywordHit struct {
	ChunkID string  `json:"chunk_id"`
	Owner   string  `json:"owner"`
	Score   float32 `json:"score"`
	Text    string  `json:"text"`
	// DocumentID and Position are the citation, carried for the same reason
	// the vector hit carries it.
	DocumentID string `json:"document_id"`
	Position   int    `json:"position"`
}

// Search returns the top-k chunks in the owner's partition by BM25.
//
// The owner is the search key. A query for a term that only appears in
// another owner's chunks returns nothing, because the postings are consulted
// only for chunk ids inside the partition.
func (ki *KeywordIndex) Search(owner, query string, k int) []KeywordHit {
	if k <= 0 {
		return nil
	}
	terms := Tokenize(query)
	if len(terms) == 0 {
		return nil
	}

	ki.corpus.mu.RLock()
	partition := make([]string, 0, len(ki.corpus.byOwner[owner]))
	for cid := range ki.corpus.byOwner[owner] {
		partition = append(partition, cid)
	}
	ki.corpus.mu.RUnlock()
	if len(partition) == 0 {
		return nil
	}

	ki.mu.RLock()
	n := len(ki.tf)

	// Score every chunk in the partition that shares at least one query term.
	// The partition is walked rather than the postings, because a query with
	// several terms needs the union and the partition is usually the smaller
	// of the two once the owner is scoped.
	idfs := make(map[string]float32, len(terms))
	for _, term := range terms {
		idfs[term] = ki.idf(term, n)
	}

	var avgdl float32
	if n > 0 {
		avgdl = float32(ki.totalLength) / float32(n)
	}

	candidates := make([]KeywordHit, 0, len(partition))
	for _, cid := range partition {
		freq := ki.tf[cid]
		if len(freq) == 0 {
			continue
		}
		dl := float32(ki.lengths[cid])
		var score float32
		for _, term := range terms {
			f := freq[term]
			if f == 0 {
				continue
			}
			idf := idfs[term]
			norm := bm25K1 * (1 - bm25B + bm25B*dl/avgdl)
			score += idf * (float32(f) * (bm25K1 + 1)) / (float32(f) + norm)
		}
		if score <= 0 {
			continue
		}
		ki.mu.RUnlock()
		chunk := ki.corpus.chunk(cid)
		ki.mu.RLock()
		if chunk == nil {
			continue
		}
		candidates = append(candidates, KeywordHit{
			ChunkID:    cid,
			Owner:      chunk.Owner,
			Score:      score,
			Text:       chunk.Text,
			DocumentID: chunk.DocumentID,
			Position:   chunk.Position,
		})
	}
	ki.mu.RUnlock()

	sort.Slice(candidates, func(i, j int) bool {
		if candidates[i].Score != candidates[j].Score {
			return candidates[i].Score > candidates[j].Score
		}
		// Ties broken by chunk id so two identical queries rank alike.
		return candidates[i].ChunkID < candidates[j].ChunkID
	})
	if k > len(candidates) {
		k = len(candidates)
	}
	return candidates[:k]
}

// chunk is a corpus read that does not take the corpus lock, for callers that
// already hold it or that take it themselves. See Search above: the corpus
// lock is released and retaken around the read so the keyword lock is never
// held across the corpus lock, which is how the two are ordered everywhere
// else in this package and therefore how deadlock is avoided.
func (c *Corpus) chunk(id string) *Chunk {
	k := c.chunks[id]
	if k == nil {
		return nil
	}
	out := *k
	return &out
}
