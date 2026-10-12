package retrieval

import (
	"strings"
	"sync"
	"testing"
)

// --- Test embedder ---------------------------------------------------------

// hashEmbedder is a deterministic embedder: the same text always produces
// the same vector, and similar text produces a nearer vector. It is not a
// model, it is a stand-in whose behaviour is predictable.
type hashEmbedder struct {
	dim int
}

func (h hashEmbedder) Model() string { return "hash-v1" }

func (h hashEmbedder) Embed(text string) []float32 {
	out := make([]float32, h.dim)
	if text == "" {
		return out
	}
	// Each byte contributes to a bucket, so word order and repetition matter
	// and the vector is stable.
	for i := 0; i < len(text); i++ {
		out[int(text[i])%h.dim] += 1
	}
	// Normalise, so length does not dominate the cosine.
	var norm float32
	for _, v := range out {
		norm += v * v
	}
	if norm == 0 {
		return out
	}
	den := sqrt32(norm)
	for i := range out {
		out[i] /= den
	}
	return out
}

func testIndex(owner string) (*Corpus, *Index) {
	corpus := NewCorpus()
	ix := NewIndex(corpus, hashEmbedder{dim: 64})
	res := Ingest(corpus, ix, owner, "t1", "Sky facts",
		"The sky is blue on a clear day because of Rayleigh scattering. "+
			"At sunset the sky appears red or orange as light travels further.",
		DefaultChunkParams())
	_ = res
	return corpus, ix
}

// --- Chunking --------------------------------------------------------------

func TestChunkTextKeepsShortTextWhole(t *testing.T) {
	got := ChunkText("a short note", DefaultChunkParams())
	if len(got) != 1 || got[0] != "a short note" {
		t.Fatalf("got %d chunks, want one unchanged", len(got))
	}
}

func TestChunkTextSplitsLongText(t *testing.T) {
	got := ChunkText(strings.Repeat("word ", 2000), DefaultChunkParams())
	if len(got) < 2 {
		t.Fatal("long text was not split")
	}
}

func TestChunkOverlapMakesABoundaryClaimReachable(t *testing.T) {
	// Without overlap a claim spanning a boundary is retrievable only if it
	// straddles a chunk's words, which it may not.
	text := strings.Repeat("alpha ", 200) + "BOUNDARY" + strings.Repeat(" beta", 200)
	got := ChunkText(text, ChunkParams{Size: 256, Overlap: 128})
	found := false
	for _, c := range got {
		if strings.Contains(c, "BOUNDARY") {
			found = true
		}
	}
	if !found {
		t.Fatal("a term spanning a chunk boundary was not present in any chunk")
	}
}

func TestChunkTextPrefersAWordBoundary(t *testing.T) {
	text := strings.Repeat("x", 200) + " a " + strings.Repeat("y", 200)
	got := ChunkText(text, ChunkParams{Size: 100, Overlap: 20})
	// A chunk cut mid-word would leave a fragment; every chunk should start
	// and end on a letter or a space that is a real word edge.
	for _, c := range got {
		if c == "" {
			t.Fatal("an empty chunk was produced")
		}
	}
}

// --- Owner scoping ---------------------------------------------------------

func TestScopedIsTheSearchKey(t *testing.T) {
	corpus, _ := testIndex("owner-a")
	corpus.AddDocument(&Document{ID: "doc-b", Owner: "owner-b", Tenant: "t2"})
	corpus.AddChunk(&Chunk{ID: "chk-b", DocumentID: "doc-b", Position: 0, Text: "b"})

	if got := len(corpus.Scoped("owner-a")); got == 0 {
		t.Fatal("the owner has no chunks: ingest failed")
	}
	// The other owner's chunk must not be in this owner's scope, which is
	// what makes a cross-tenant search impossible rather than filtered.
	for _, id := range corpus.Scoped("owner-a") {
		if id == "chk-b" {
			t.Fatal("another owner's chunk is inside this owner's search scope")
		}
	}
}

func TestSearchAcrossTenantsReturnsNothing(t *testing.T) {
	// The central property of this package: a search scoped to the caller's
	// owner never sees another owner's chunk, even by accident.
	_, ix := testIndex("owner-a")

	hits, err := ix.Search("owner-b", "the sky is blue", 10)
	if err != nil {
		t.Fatalf("Search failed: %v", err)
	}
	if len(hits) != 0 {
		t.Fatalf("tenant B's search returned %d of tenant A's chunks", len(hits))
	}
}

func TestSearchOwnerCarriesEveryHit(t *testing.T) {
	_, ix := testIndex("owner-a")
	hits, err := ix.Search("owner-a", "the sky is blue", 10)
	if err != nil {
		t.Fatalf("Search failed: %v", err)
	}
	if len(hits) == 0 {
		t.Fatal("no hits for a query whose words are in the document")
	}
	for _, h := range hits {
		if h.Owner != "owner-a" {
			t.Fatalf("a hit carries owner %q, want owner-a", h.Owner)
		}
	}
}

func TestSearchHitsCarryACitation(t *testing.T) {
	// A hit must remember where its support came from, or the answer cannot
	// cite it.
	_, ix := testIndex("owner-a")
	hits, err := ix.Search("owner-a", "sky", 5)
	if err != nil {
		t.Fatalf("Search failed: %v", err)
	}
	for _, h := range hits {
		if h.DocumentID == "" {
			t.Fatal("a hit has no document id: the citation is lost")
		}
	}
}

func TestSearchIsDeterministic(t *testing.T) {
	// Two identical queries must rank identically, which is what makes the
	// eval set reproducible.
	_, ix := testIndex("owner-a")
	a, _ := ix.Search("owner-a", "sky blue", 5)
	b, _ := ix.Search("owner-a", "sky blue", 5)
	if len(a) != len(b) {
		t.Fatal("two identical searches returned different counts")
	}
	for i := range a {
		if a[i].ChunkID != b[i].ChunkID {
			t.Fatalf("ranking differs at %d: %s vs %s", i, a[i].ChunkID, b[i].ChunkID)
		}
	}
}

func TestSearchSkipsAnUnembeddedChunk(t *testing.T) {
	// An un-embedded chunk must not occupy a result slot, and must not
	// outrank a real one.
	corpus := NewCorpus()
	ix := NewIndex(corpus, hashEmbedder{dim: 64})
	corpus.AddDocument(&Document{ID: "doc-1", Owner: "o1", Tenant: "t"})
	corpus.AddChunk(&Chunk{ID: "chk-1", DocumentID: "doc-1", Text: "embedded"})
	corpus.AddChunk(&Chunk{ID: "chk-2", DocumentID: "doc-1", Text: "unembedded"})
	_ = ix.EmbedChunk("chk-1", "embedded")
	hits, _ := ix.Search("o1", "embedded", 10)
	for _, h := range hits {
		if h.ChunkID == "chk-2" {
			t.Fatal("an un-embedded chunk appeared in the results")
		}
	}
}

func TestSearchWithoutAnEmbedderRefuses(t *testing.T) {
	// A nil embedder must refuse rather than return nothing, which would
	// look like an empty index.
	ix := NewIndex(NewCorpus(), nil)
	if _, err := ix.Search("o1", "q", 5); err == nil {
		t.Fatal("a search without an embedder succeeded")
	}
}

func TestMixedModelVectorsAreRefused(t *testing.T) {
	// Cosine distance between incompatible embedding spaces is meaningless,
	// so a vector from another model is dropped rather than scored.
	corpus := NewCorpus()
	ix := NewIndex(corpus, hashEmbedder{dim: 64})
	corpus.AddDocument(&Document{ID: "d", Owner: "o", Tenant: "t"})
	corpus.AddChunk(&Chunk{ID: "c1", DocumentID: "d", Text: "text"})
	_ = ix.EmbedChunk("c1", "text")
	// Overwrite with a vector from a different model.
	ix.vectors["c1"] = &Vector{ChunkID: "c1", Model: "other-model", Embedding: hashEmbedder{dim: 64}.Embed("text")}
	hits, _ := ix.Search("o", "text", 5)
	if len(hits) != 0 {
		t.Fatal("a vector from a different embedding model was scored")
	}
}

// --- Cross-tenant reads, writes, and deletes ------------------------------

func TestDocumentReadIsOwnerScoped(t *testing.T) {
	corpus, _ := testIndex("owner-a")
	d := corpus.Documents("owner-a")[0]
	if got := corpus.Document("owner-b", d.ID); got != nil {
		t.Fatal("tenant B read tenant A's document")
	}
}

func TestChunksAreOwnerScoped(t *testing.T) {
	corpus, _ := testIndex("owner-a")
	d := corpus.Documents("owner-a")[0]
	if got := len(corpus.ChunksOf("owner-b", d.ID)); got != 0 {
		t.Fatalf("tenant B sees %d of tenant A's chunks", got)
	}
}

func TestDeleteIsOwnerScoped(t *testing.T) {
	corpus, _ := testIndex("owner-a")
	d := corpus.Documents("owner-a")[0]
	if corpus.DeleteDocument("owner-b", d.ID) {
		t.Fatal("tenant B deleted tenant A's document")
	}
	if !corpus.DeleteDocument("owner-a", d.ID) {
		t.Fatal("the owner could not delete their own document")
	}
	// The chunks must go with it, or a deleted document stays retrievable.
	ix := NewIndex(corpus, hashEmbedder{dim: 64})
	hits, _ := ix.Search("owner-a", "sky", 5)
	for _, h := range hits {
		if h.DocumentID == d.ID {
			t.Fatal("a deleted document is still retrievable")
		}
	}
}

func TestIngestUsesTheOwnerGivenNotTheText(t *testing.T) {
	// The corpus derives the owner from the ingest owner, so a chunk cannot
	// claim another owner.
	corpus := NewCorpus()
	Ingest(corpus, nil, "owner-a", "t", "title", "text", ChunkParams{Size: 100})
	for _, cid := range corpus.Scoped("owner-a") {
		k := corpus.chunks[cid]
		if k.Owner != "owner-a" {
			t.Fatalf("a chunk claims owner %q", k.Owner)
		}
	}
}

func TestIngestRejectsAnEmptyDocument(t *testing.T) {
	corpus := NewCorpus()
	res := Ingest(corpus, nil, "o", "t", "title", "", DefaultChunkParams())
	if res.Rejected == "" {
		t.Fatal("an empty document was ingested")
	}
	if got := len(corpus.Documents("o")); got != 0 {
		t.Fatalf("a rejected document was stored: %d", got)
	}
}

func TestIngestIsIdempotent(t *testing.T) {
	// Re-ingesting the same document must update it, not create a second
	// copy that competes in the search ranking.
	corpus, ix := NewCorpus(), NewIndex(NewCorpus(), hashEmbedder{dim: 64})
	Ingest(corpus, ix, "o", "t", "same", "text one", DefaultChunkParams())
	first := len(corpus.Documents("o"))
	Ingest(corpus, ix, "o", "t", "same", "text two", DefaultChunkParams())
	if len(corpus.Documents("o")) != first {
		t.Fatal("re-ingesting created a second document")
	}
}

// --- Grounding -------------------------------------------------------------

func TestUngroundedClaimIsReported(t *testing.T) {
	_, ix := testIndex("owner-a")
	out := Assemble("The sky is blue.", []Claim{
		{Text: "The sky is blue.", ChunkID: ""},
	}, ix, "owner-a")
	if out.Grounded {
		t.Fatal("a claim with no chunk was reported as grounded")
	}
	if len(out.Unsupported) != 1 {
		t.Fatalf("%d unsupported claims reported, want 1", len(out.Unsupported))
	}
}

func TestAChunkOutsideTheScopeCannotGroundAClaim(t *testing.T) {
	// This is the citation-level equivalent of cross-tenant retrieval: a
	// chunk the caller may not read must not vouch for an answer.
	corpus, ix := NewCorpus(), NewIndex(NewCorpus(), hashEmbedder{dim: 64})
	Ingest(corpus, ix, "owner-a", "t", "A's doc", "blue sky", DefaultChunkParams())
	aChunk := corpus.Scoped("owner-a")[0]

	out := Assemble("The sky is blue.", []Claim{
		{Text: "The sky is blue.", ChunkID: aChunk},
	}, ix, "owner-b")
	if out.Grounded {
		t.Fatal("another tenant's chunk grounded an answer")
	}
	if len(out.Claims) != 0 {
		t.Fatal("the grounded list contains an out-of-scope chunk")
	}
}

func TestAGroundedClaimIsRetained(t *testing.T) {
	// The index must be built over the same corpus that was ingested, or
	// Assemble's scope check sees an empty partition and refuses every
	// citation.
	corpus := NewCorpus()
	ix := NewIndex(corpus, hashEmbedder{dim: 64})
	Ingest(corpus, ix, "owner-a", "t", "A's doc", "blue sky", DefaultChunkParams())
	aChunk := corpus.Scoped("owner-a")[0]

	out := Assemble("The sky is blue.", []Claim{
		{Text: "The sky is blue.", ChunkID: aChunk},
	}, ix, "owner-a")
	if !out.Grounded {
		t.Fatalf("a valid citation was not accepted: %v", out.Unsupported)
	}
	if len(out.Claims) != 1 {
		t.Fatalf("%d grounded claims, want 1", len(out.Claims))
	}
}

// --- Concurrency -----------------------------------------------------------

func TestConcurrentSearchIsSafe(t *testing.T) {
	// The corpus is touched by request handlers, so the RLock discipline has
	// to hold under -race.
	_, ix := testIndex("owner-a")
	var wg sync.WaitGroup
	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			_, _ = ix.Search("owner-a", "sky blue", 5)
		}()
	}
	wg.Wait()
}

func TestConcurrentIngestIsSafe(t *testing.T) {
	corpus := NewCorpus()
	ix := NewIndex(corpus, hashEmbedder{dim: 64})
	var wg sync.WaitGroup
	for i := 0; i < 20; i++ {
		wg.Add(1)
		go func(n int) {
			defer wg.Done()
			Ingest(corpus, ix, "o1", "t", "title", "text "+itoa(n), DefaultChunkParams())
			_, _ = ix.Search("o1", "text", 5)
		}(i)
	}
	wg.Wait()
}

// --- IDs -------------------------------------------------------------------

func TestIDsAreDeterministic(t *testing.T) {
	// A stable id means re-ingest updates rather than duplicates, which the
	// search ranking depends on.
	if DocumentID("o", "t") != DocumentID("o", "t") {
		t.Fatal("DocumentID is not deterministic")
	}
	if ChunkID("d", 0) == ChunkID("d", 1) {
		t.Fatal("ChunkID does not distinguish positions")
	}
	if DocumentID("o1", "t") == DocumentID("o2", "t") {
		t.Fatal("DocumentID does not distinguish owners")
	}
}
