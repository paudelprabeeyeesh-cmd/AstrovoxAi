package retrieval

import (
	"strings"
	"testing"
)

// hybridFixture builds a corpus where the two retrieval paths disagree, which
// is the only case worth testing: if they agreed, a single path would do.
//
// "alpha" and "beta" share a term, "gamma" shares none. The vector embedder is
// a bag-of-characters, so it ranks on orthographic overlap and cannot tell a
// synonym from an unrelated word; BM25 ranks on exact terms and cannot tell a
// paraphrase from a miss. Each therefore finds something the other misses.
func hybridFixture(t *testing.T, owner string) (*Corpus, *Index, *KeywordIndex) {
	t.Helper()
	corpus := NewCorpus()
	embed := NewHashEmbeddable(64)
	ix := NewIndex(corpus, embed)
	ki := NewKeywordIndex(corpus)

	docs := []struct {
		title string
		text  string
	}{
		{"exact", "credential rotation procedure for postgres"},
		{"paraphrase", "how to roll over database secrets safely"},
		{"unrelated", "the weather in oporto is mild in spring"},
	}
	for i, d := range docs {
		id := DocumentID(owner, d.title)
		corpus.AddDocument(&Document{
			ID:     id,
			Owner:  owner,
			Tenant: "t1",
			Title:  d.title,
		})
		span := ChunkText(d.text, ChunkParams{Size: 512, Overlap: 0})[0]
		cid := ChunkID(id, 0)
		corpus.AddChunk(&Chunk{
			ID:         cid,
			DocumentID: id,
			Owner:      owner,
			Tenant:    "t1",
			Position:   i,
			Text:       span,
		})
		_ = ix.EmbedChunk(cid, span)
		ki.AddChunk(cid, span)
	}
	return corpus, ix, ki
}

func chunkIDs(hits []HybridHit) []string {
	out := make([]string, 0, len(hits))
	for _, h := range hits {
		out = append(out, h.ChunkID)
	}
	return out
}

func TestTokenizeNormalisesCaseAndPunctuation(t *testing.T) {
	got := Tokenize("PostgreSQL's SECRETS, are--rotated; by/ops")
	want := []string{"postgresql", "s", "secrets", "are", "rotated", "by", "ops"}
	if strings.Join(got, " ") != strings.Join(want, " ") {
		t.Fatalf("got %q, want %q", got, want)
	}
}

func TestTokenizeKeepsUnicodeLetters(t *testing.T) {
	// Non-ASCII letters must not be split into punctuation-sized pieces. A
	// bytes.IsAlnum style classifier treats any byte above 0x7F as a separator,
	// which silently breaks every non-Latin script.
	got := Tokenize("中文 words")
	if len(got) != 2 || got[0] != "中文" {
		t.Fatalf("non-latin letters were split: %q", got)
	}
	cyrillic := Tokenize("привет")
	if len(cyrillic) != 1 || cyrillic[0] != "привет" {
		t.Fatalf("cyrillic word was split: %q", cyrillic)
	}
}

func TestTokenizeDropsPunctuationOnly(t *testing.T) {
	if len(Tokenize("  ...--;; ")) != 0 {
		t.Fatal("punctuation produced terms")
	}
}

func TestKeywordIndexFindsAnExactTerm(t *testing.T) {
	corpus, _, ki := hybridFixture(t, "u1")
	_ = corpus

	hits := ki.Search("u1", "rotation", 10)
	if len(hits) != 1 {
		t.Fatalf("expected the one chunk containing 'rotation', got %d", len(hits))
	}
	if !strings.Contains(hits[0].Text, "rotation") {
		t.Fatalf("wrong chunk: %q", hits[0].Text)
	}
}

func TestKeywordSearchIsOwnerScoped(t *testing.T) {
	// The same term must be visible to its own owner and invisible to the
	// other. This is the property that makes the keyword path safe to expose
	// without a post-filter.
	corpus := NewCorpus()
	ki := NewKeywordIndex(corpus)
	for _, owner := range []string{"u1", "u2"} {
		id := DocumentID(owner, "doc")
		corpus.AddDocument(&Document{ID: id, Owner: owner, Tenant: owner})
		cid := ChunkID(id, 0)
		corpus.AddChunk(&Chunk{ID: cid, DocumentID: id, Owner: owner, Text: "shared term here"})
		ki.AddChunk(cid, "shared term here")
	}

	if got := ki.Search("u1", "shared", 10); len(got) != 1 || got[0].Owner != "u1" {
		t.Fatalf("owner u1 saw %d hits, owner=%q", len(got), ownerOf(got))
	}
	if got := ki.Search("u2", "shared", 10); len(got) != 1 || got[0].Owner != "u2" {
		t.Fatalf("owner u2 saw %d hits, owner=%q", len(got), ownerOf(got))
	}
	if got := ki.Search("u3", "shared", 10); got != nil && len(got) != 0 {
		t.Fatalf("an unknown owner saw %d hits", len(got))
	}
}

func ownerOf(hits []KeywordHit) string {
	if len(hits) == 0 {
		return "<none>"
	}
	return hits[0].Owner
}

func TestBM25RanksAMoreRelevantChunkFirst(t *testing.T) {
	// Three chunks, one containing the query term three times, one once, one
	// not at all. The one with more occurrences must rank first, and the
	// irrelevant one must not appear.
	corpus := NewCorpus()
	ki := NewKeywordIndex(corpus)
	texts := []string{
		"token token token and other words to pad the length",
		"token appears once in this otherwise unrelated chunk",
		"nothing relevant is said here at all in this chunk",
	}
	for i, text := range texts {
		id := DocumentID("u1", "d")
		cid := ChunkID(id, i)
		corpus.AddDocument(&Document{ID: id, Owner: "u1", Tenant: "u1"})
		corpus.AddChunk(&Chunk{ID: cid, DocumentID: id, Owner: "u1", Position: i, Text: text})
		ki.AddChunk(cid, text)
	}

	hits := ki.Search("u1", "token", 3)
	if len(hits) == 0 {
		t.Fatal("no hits for a term that exists")
	}
	if !strings.HasPrefix(hits[0].Text, "token token token") {
		t.Fatalf("the repeated-term chunk did not rank first: %q", hits[0].Text)
	}
	if hits[0].Score <= hits[len(hits)-1].Score {
		t.Fatal("scores did not decrease with relevance")
	}
}

func TestBM25IDFDoesNotFavourAUniversalTerm(t *testing.T) {
	// A term in every document carries no information, so it must not
	// dominate a term unique to one document. Without smoothing, a universal
	// term gets IDF 0 and vanishes; without the +1 it can go negative.
	corpus := NewCorpus()
	ki := NewKeywordIndex(corpus)
	texts := []string{
		"the common filler word and unique alpha term",
		"the common filler word alone",
		"the common filler word again here",
	}
	for i, text := range texts {
		id := DocumentID("u1", "d")
		cid := ChunkID(id, i)
		corpus.AddDocument(&Document{ID: id, Owner: "u1", Tenant: "u1"})
		corpus.AddChunk(&Chunk{ID: cid, DocumentID: id, Owner: "u1", Position: i, Text: text})
		ki.AddChunk(cid, text)
	}

	hits := ki.Search("u1", "the alpha", 3)
	if len(hits) == 0 {
		t.Fatal("no hits")
	}
	if !strings.Contains(hits[0].Text, "alpha") {
		t.Fatalf("the chunk with the distinctive term did not rank first: %q", hits[0].Text)
	}
}

func TestKeywordIndexReplaceDropsStaleTerms(t *testing.T) {
	// Re-indexing an updated chunk must forget its old terms, or the chunk
	// keeps matching queries it no longer contains.
	corpus := NewCorpus()
	ki := NewKeywordIndex(corpus)
	id := DocumentID("u1", "d")
	cid := ChunkID(id, 0)
	corpus.AddDocument(&Document{ID: id, Owner: "u1", Tenant: "u1"})
	corpus.AddChunk(&Chunk{ID: cid, DocumentID: id, Owner: "u1", Text: "old term"})
	ki.AddChunk(cid, "old term")

	ki.AddChunk(cid, "new term")
	if got := ki.Search("u1", "old", 10); len(got) != 0 {
		t.Fatalf("a stale term still matched %d chunks", len(got))
	}
	if got := ki.Search("u1", "new", 10); len(got) != 1 {
		t.Fatalf("the updated term matched %d chunks", len(got))
	}
	if ki.Len() != 1 {
		t.Fatalf("re-indexing changed the chunk count to %d", ki.Len())
	}
}

func TestKeywordIndexRemoveForgetsTheChunk(t *testing.T) {
	corpus, _, ki := hybridFixture(t, "u1")
	_ = corpus
	before := len(ki.Search("u1", "rotation", 10))
	if before == 0 {
		t.Fatal("fixture has no rotation hits")
	}
	ki.RemoveChunk(ChunkID(DocumentID("u1", "exact"), 0))
	if got := ki.Search("u1", "rotation", 10); len(got) != 0 {
		t.Fatalf("a removed chunk still matched: %d", len(got))
	}
}

func TestHybridFindsWhatEitherPathMissesAlone(t *testing.T) {
	// The fusion must surface a result that only one path would have
	// returned. On this fixture the vector path ranks the paraphrase first
	// and the keyword path ranks the exact-term chunk first; fused, both must
	// appear, which neither path alone reliably does.
	corpus, ix, ki := hybridFixture(t, "u1")
	_ = corpus

	vectorOnly, err := ix.Search("u1", "credential rotation", 3)
	if err != nil {
		t.Fatalf("vector search failed: %v", err)
	}
	keywordOnly := ki.Search("u1", "credential rotation", 3)

	hybrid, err := HybridQuery(ix, ki, "u1", "credential rotation", 3, DefaultHybridParams())
	if err != nil {
		t.Fatalf("hybrid search failed: %v", err)
	}
	if len(hybrid) == 0 {
		t.Fatal("hybrid returned nothing")
	}

	seen := map[string]bool{}
	for _, h := range hybrid {
		seen[h.ChunkID] = true
	}
	// Every hit from either path must survive the fusion.
	for _, h := range append(vectorOnly, hybridToVector(keywordOnly)...) {
		if !seen[h.ChunkID] {
			t.Fatalf("fusion dropped a hit both paths found: %s", h.ChunkID)
		}
	}
}

// hybridToVector adapts keyword hits to the vector hit shape so the
// comparison above can iterate both lists.
func hybridToVector(in []KeywordHit) []Hit {
	out := make([]Hit, 0, len(in))
	for _, h := range in {
		out = append(out, Hit{ChunkID: h.ChunkID, Owner: h.Owner, Score: h.Score})
	}
	return out
}

func TestHybridKeepsAHitOnlyOnePathFound(t *testing.T) {
	// The paraphrase shares no term with the query, so the keyword path
	// cannot find it; the vector path can. The fused ranking must still
	// contain it and must record that only the vector path produced it.
	_, ix, ki := hybridFixture(t, "u1")

	hybrid, err := HybridQuery(ix, ki, "u1", "credential rotation", 3, DefaultHybridParams())
	if err != nil {
		t.Fatalf("hybrid search failed: %v", err)
	}
	var vectorOnlyHit *HybridHit
	for i := range hybrid {
		h := hybrid[i]
		if h.FromVector && !h.FromKeyword {
			vectorOnlyHit = &h
		}
	}
	if vectorOnlyHit == nil {
		t.Fatal("no vector-only hit survived the fusion")
	}
	if !strings.Contains(vectorOnlyHit.Text, "roll over") {
		t.Fatalf("the wrong chunk was vector-only: %q", vectorOnlyHit.Text)
	}
}

func TestHybridAgreesWhenBothPathsFindTheSameChunk(t *testing.T) {
	// A chunk both paths rank first must be fused first, and must be flagged
	// as coming from both, which is the signal that the ranking is trustworthy.
	corpus := NewCorpus()
	_ = corpus
	embed := NewHashEmbeddable(64)
	ix := NewIndex(corpus, embed)
	ki := NewKeywordIndex(corpus)

	id := DocumentID("u1", "only")
	corpus.AddDocument(&Document{ID: id, Owner: "u1", Tenant: "u1"})
	cid := ChunkID(id, 0)
	corpus.AddChunk(&Chunk{ID: cid, DocumentID: id, Owner: "u1", Text: "solitary chunk"})
	_ = ix.EmbedChunk(cid, "solitary chunk")
	ki.AddChunk(cid, "solitary chunk")

	hybrid, err := HybridQuery(ix, ki, "u1", "solitary", 5, DefaultHybridParams())
	if err != nil {
		t.Fatalf("hybrid search failed: %v", err)
	}
	if len(hybrid) != 1 {
		t.Fatalf("expected one hit, got %d", len(hybrid))
	}
	if !hybrid[0].FromVector || !hybrid[0].FromKeyword {
		t.Fatal("the single chunk was not attributed to both paths")
	}
}

func TestHybridIsOwnerScoped(t *testing.T) {
	// The access control must survive fusion: neither path may see another
	// owner's chunks, and the fused result must not either.
	corpus := NewCorpus()
	embed := NewHashEmbeddable(64)
	ix := NewIndex(corpus, embed)
	ki := NewKeywordIndex(corpus)
	for _, owner := range []string{"u1", "u2"} {
		id := DocumentID(owner, "d")
		corpus.AddDocument(&Document{ID: id, Owner: owner, Tenant: owner})
		cid := ChunkID(id, 0)
		corpus.AddChunk(&Chunk{ID: cid, DocumentID: id, Owner: owner, Text: "shared query text"})
		_ = ix.EmbedChunk(cid, "shared query text")
		ki.AddChunk(cid, "shared query text")
	}

	for _, owner := range []string{"u1", "u2"} {
		hits, err := HybridQuery(ix, ki, owner, "shared query", 10, DefaultHybridParams())
		if err != nil {
			t.Fatalf("hybrid search failed for %s: %v", owner, err)
		}
		if len(hits) != 1 {
			t.Fatalf("%s saw %d hits", owner, len(hits))
		}
		if hits[0].Owner != owner {
			t.Fatalf("%s was served %s's chunk", owner, hits[0].Owner)
		}
	}
}

func TestHybridWeightsDisableAPath(t *testing.T) {
	// A zero weight is how one path is turned off, and it must behave exactly
	// like calling that path alone.
	_, ix, ki := hybridFixture(t, "u1")

	params := HybridParams{VectorWeight: 0, KeywordWeight: 1}
	hybrid, err := HybridQuery(ix, ki, "u1", "credential rotation", 10, params)
	if err != nil {
		t.Fatalf("hybrid search failed: %v", err)
	}
	keywordOnly := ki.Search("u1", "credential rotation", 10)
	if len(hybrid) != len(keywordOnly) {
		t.Fatalf("keyword-only fusion returned %d, direct keyword returned %d", len(hybrid), len(keywordOnly))
	}
	for i := range hybrid {
		if hybrid[i].FromVector {
			t.Fatal("a zero vector weight still produced a vector hit")
		}
	}

	params = HybridParams{VectorWeight: 1, KeywordWeight: 0}
	hybrid, err = HybridQuery(ix, ki, "u1", "credential rotation", 10, params)
	if err != nil {
		t.Fatalf("hybrid search failed: %v", err)
	}
	for i := range hybrid {
		if hybrid[i].FromKeyword {
			t.Fatal("a zero keyword weight still produced a keyword hit")
		}
	}
}

func TestHybridRankIsDeterministic(t *testing.T) {
	// Two identical queries must rank alike, or a user sees results reorder
	// between refreshes and no cache can be trusted.
	_, ix, ki := hybridFixture(t, "u1")

	first := chunkIDs(mustHybrid(t, ix, ki, "credential rotation"))
	second := chunkIDs(mustHybrid(t, ix, ki, "credential rotation"))
	if strings.Join(first, ",") != strings.Join(second, ",") {
		t.Fatalf("ranking changed between identical queries:\n%s\n%s", first, second)
	}
}

func mustHybrid(t *testing.T, ix *Index, ki *KeywordIndex, query string) []HybridHit {
	t.Helper()
	hits, err := HybridQuery(ix, ki, "u1", query, 5, DefaultHybridParams())
	if err != nil {
		t.Fatalf("hybrid search failed: %v", err)
	}
	return hits
}

func TestHybridCarriesACitation(t *testing.T) {
	// A fused result must still point at the document and position it came
	// from, or an answer built on it cannot be grounded.
	corpus, ix, ki := hybridFixture(t, "u1")
	_ = corpus
	hits := mustHybrid(t, ix, ki, "credential rotation")
	if len(hits) == 0 {
		t.Fatal("no hits")
	}
	for _, h := range hits {
		if h.DocumentID == "" {
			t.Fatalf("hit %s carries no document id", h.ChunkID)
		}
		if h.Text == "" {
			t.Fatalf("hit %s carries no text", h.ChunkID)
		}
	}
}

func TestHybridEmptyQueryReturnsNothing(t *testing.T) {
	_, ix, ki := hybridFixture(t, "u1")
	hits, err := HybridQuery(ix, ki, "u1", "   ", 5, DefaultHybridParams())
	if err != nil {
		t.Fatalf("an empty query should not error: %v", err)
	}
	if len(hits) != 0 {
		t.Fatalf("an empty query returned %d hits", len(hits))
	}
}

func TestHybridUnknownOwnerReturnsNothing(t *testing.T) {
	_, ix, ki := hybridFixture(t, "u1")
	hits, err := HybridQuery(ix, ki, "nobody", "credential rotation", 5, DefaultHybridParams())
	if err != nil {
		t.Fatalf("unknown owner should not error: %v", err)
	}
	if len(hits) != 0 {
		t.Fatalf("an unknown owner received %d hits", len(hits))
	}
}

func TestHybridScoresAreBounded(t *testing.T) {
	// Each path contributes at most 1/k, so with both paths at weight 1 a hit
	// cannot exceed 2/k. An unbounded score means a weight was applied twice.
	_, ix, ki := hybridFixture(t, "u1")
	hits := mustHybrid(t, ix, ki, "credential rotation")
	for _, h := range hits {
		if h.Score > 2.0/float32(rrfK)+0.0001 {
			t.Fatalf("score %v exceeds the 2/k bound", h.Score)
		}
	}
}
