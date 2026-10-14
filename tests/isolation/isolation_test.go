// Package isolation contains the adversarial cross-tenant retrieval suite.
//
// This is not a re-test of the happy path. It is an attacker's suite: every
// test asks a variant of "can I reach a chunk that is not mine?", using the
// specific mistakes that produce a leak in retrieval systems - a scope taken
// from the request, a filter applied after scoring, an index that forgot the
// owner, a delete that cascades across partitions, or a query that returns
// everything when the owner is unknown.
//
// It lives in its own package on purpose: a leak here is a data breach, and it
// must not be possible to disable it by changing how another package's
// helpers are called.
package isolation

import (
	"strings"
	"sync"
	"testing"

	"github.com/astrovox/astrovox/internal/retrieval"
)

// seedTwoTenants builds two owners with distinguishable documents. The texts
// are deliberately chosen so a naive scorer would rank the other owner's chunk
// highly: the terms overlap and the length is similar, so a leak is a ranking
// problem as well as a filter problem.
func seedTwoTenants(t *testing.T) (*retrieval.Corpus, *retrieval.Index, *retrieval.KeywordIndex) {
	t.Helper()
	corpus := retrieval.NewCorpus()
	embed := retrieval.NewHashEmbeddable(64)
	ix := retrieval.NewIndex(corpus, embed)
	ki := retrieval.NewKeywordIndex(corpus)

	secret := map[string]string{
		"tenant-a": "quarterly revenue targets for the apac region",
		"tenant-b": "quarterly revenue targets for the emea region",
	}
	for owner, text := range secret {
		id := retrieval.DocumentID(owner, "secret")
		corpus.AddDocument(&retrieval.Document{ID: id, Owner: owner, Tenant: owner, Title: "secret"})
		span := retrieval.ChunkText(text, retrieval.ChunkParams{Size: 512, Overlap: 0})[0]
		cid := retrieval.ChunkID(id, 0)
		corpus.AddChunk(&retrieval.Chunk{
			ID: cid, DocumentID: id, Owner: owner, Tenant: owner, Position: 0, Text: span,
		})
		_ = ix.EmbedChunk(cid, span)
		ki.AddChunk(cid, span)
	}
	return corpus, ix, ki
}

func owns(t *testing.T, hits []retrieval.HybridHit, owner string) {
	t.Helper()
	for _, h := range hits {
		if h.Owner != owner {
			t.Fatalf("tenant %s was served %s's chunk %s", owner, h.Owner, h.ChunkID)
		}
	}
}

func TestVectorSearchCannotReachAnotherTenant(t *testing.T) {
	corpus, ix, ki := seedTwoTenants(t)
	_, _, _ = corpus, ix, ki

	hits, err := ix.Search("tenant-a", "quarterly revenue targets emea", 10)
	if err != nil {
		t.Fatalf("search failed: %v", err)
	}
	if len(hits) == 0 {
		t.Fatal("the owner's own chunk was not found; the fixture is broken")
	}
	for _, h := range hits {
		if strings.Contains(h.Text, "emea") {
			t.Fatalf("tenant-a matched tenant-b's chunk: %q", h.Text)
		}
		if h.Owner != "tenant-a" {
			t.Fatalf("hit carries the wrong owner %q", h.Owner)
		}
	}
}

func TestKeywordSearchCannotReachAnotherTenant(t *testing.T) {
	corpus, ix, ki := seedTwoTenants(t)
	_, _, _ = corpus, ix, ki

	// "emea" appears only in tenant-b's document, so a correct implementation
	// returns nothing for tenant-a. Returning anything is the leak.
	hits := ki.Search("tenant-a", "emea", 10)
	if len(hits) != 0 {
		t.Fatalf("tenant-a received %d hits for a term only in tenant-b", len(hits))
	}
	if len(ki.Search("tenant-b", "emea", 10)) != 1 {
		t.Fatal("tenant-b could not find its own term; the fixture is broken")
	}
}

func TestHybridSearchCannotReachAnotherTenant(t *testing.T) {
	corpus, ix, ki := seedTwoTenants(t)
	_, _, _ = corpus, ix, ki

	hits, err := retrieval.HybridQuery(ix, ki, "tenant-a", "quarterly revenue targets emea", 10, retrieval.DefaultHybridParams())
	if err != nil {
		t.Fatalf("hybrid failed: %v", err)
	}
	owns(t, hits, "tenant-a")
	for _, h := range hits {
		if strings.Contains(h.Text, "emea") {
			t.Fatalf("hybrid leaked tenant-b's text into tenant-a: %q", h.Text)
		}
	}
}

func TestAnUnknownOwnerGetsNothingRatherThanEverything(t *testing.T) {
	// The classic failure: the scope lookup misses, so the code falls through
	// to "all chunks". An unknown owner must see an empty partition.
	corpus, ix, ki := seedTwoTenants(t)
	_, _, _ = corpus, ix, ki

	if got, _ := ix.Search("attacker", "quarterly revenue", 10); len(got) != 0 {
		t.Fatalf("an unknown owner received %d vector hits", len(got))
	}
	if got := ki.Search("attacker", "quarterly revenue", 10); len(got) != 0 {
		t.Fatalf("an unknown owner received %d keyword hits", len(got))
	}
	hybrid, err := retrieval.HybridQuery(ix, ki, "attacker", "quarterly revenue", 10, retrieval.DefaultHybridParams())
	if err != nil {
		t.Fatalf("hybrid failed: %v", err)
	}
	if len(hybrid) != 0 {
		t.Fatalf("an unknown owner received %d hybrid hits", len(hybrid))
	}
}

func TestAnEmptyOwnerGetsNothingRatherThanEverything(t *testing.T) {
	// Same failure mode as above, but reachable from a request that simply
	// omits the scope entirely.
	corpus, ix, ki := seedTwoTenants(t)
	_, _, _ = corpus, ix, ki

	if got, _ := ix.Search("", "quarterly revenue", 10); len(got) != 0 {
		t.Fatalf("an empty owner received %d vector hits", len(got))
	}
	hybrid, err := retrieval.HybridQuery(ix, ki, "", "quarterly revenue", 10, retrieval.DefaultHybridParams())
	if err != nil {
		t.Fatalf("hybrid failed: %v", err)
	}
	if len(hybrid) != 0 {
		t.Fatalf("an empty owner received %d hybrid hits", len(hybrid))
	}
}

func TestADeleteCascadesOnlyWithinItsPartition(t *testing.T) {
	// Deleating tenant-a's document must not remove or expose tenant-b's.
	corpus, ix, ki := seedTwoTenants(t)

	if !corpus.DeleteDocument("tenant-a", retrieval.DocumentID("tenant-a", "secret")) {
		t.Fatal("tenant-a could not delete its own document")
	}
	if corpus.Document("tenant-b", retrieval.DocumentID("tenant-b", "secret")) == nil {
		t.Fatal("an owner-scoped delete removed another tenant's document")
	}

	hits, err := retrieval.HybridQuery(ix, ki, "tenant-b", "quarterly revenue targets", 10, retrieval.DefaultHybridParams())
	if err != nil {
		t.Fatalf("hybrid failed: %v", err)
	}
	owns(t, hits, "tenant-b")
	if len(hits) == 0 {
		t.Fatal("tenant-b lost its own chunk through another tenant's delete")
	}
}

func TestADeleteByAnotherTenantIsANoOp(t *testing.T) {
	corpus, _, _ := seedTwoTenants(t)

	if corpus.DeleteDocument("tenant-b", retrieval.DocumentID("tenant-a", "secret")) {
		t.Fatal("tenant-b deleted tenant-a's document")
	}
	if corpus.Document("tenant-a", retrieval.DocumentID("tenant-a", "secret")) == nil {
		t.Fatal("the cross-owner delete removed the document anyway")
	}
}

func TestAChunkInheritsItsDocumentsScopeNotTheCallers(t *testing.T) {
	// A chunk added with a caller-supplied owner must still inherit the
	// document's owner. Otherwise a caller can attach their chunk to another
	// owner's document and read it.
	corpus := retrieval.NewCorpus()
	docID := retrieval.DocumentID("owner-of-record", "d")
	corpus.AddDocument(&retrieval.Document{ID: docID, Owner: "owner-of-record", Tenant: "owner-of-record"})

	cid := retrieval.ChunkID(docID, 0)
	corpus.AddChunk(&retrieval.Chunk{
		ID: cid, DocumentID: docID,
		// The caller tries to claim the document.
		Owner: "attacker", Tenant: "attacker",
		Text: "should belong to the document's owner",
	})

	if got := corpus.Document("attacker", docID); got != nil {
		t.Fatal("the attacker could read the document they tried to claim")
	}
	if corpus.Document("owner-of-record", docID) == nil {
		t.Fatal("the real owner lost the document")
	}
}

func TestCitationsAreOnlyGroundedForTheOwningTenant(t *testing.T) {
	// Assemble must refuse an answer whose claim cites a chunk outside the
	// caller's partition. A leak here is not just a wrong score: it is an
	// answer presented as supported by text the caller may not read.
	corpus, ix, _ := seedTwoTenants(t)

	foreignChunk := retrieval.ChunkID(retrieval.DocumentID("tenant-b", "secret"), 0)
	answer := retrieval.Assemble("The apac target is X.", []retrieval.Claim{
		{Text: "The apac target is X.", ChunkID: foreignChunk},
	}, ix, "tenant-a")

	if answer.Grounded {
		t.Fatal("an answer citing another tenant's chunk was reported as grounded")
	}
	if len(answer.Unsupported) == 0 {
		t.Fatal("the ungrounded claim was not reported as unsupported")
	}

	own := retrieval.Assemble("The apac target is X.", []retrieval.Claim{
		{Text: "The apac target is X.", ChunkID: retrieval.ChunkID(retrieval.DocumentID("tenant-a", "secret"), 0)},
	}, ix, "tenant-a")
	if !own.Grounded {
		t.Fatalf("an owner's own citation was refused: %v", own.Unsupported)
	}
	_ = corpus
}

func TestConcurrentMixedTenantSearchNeverCrosses(t *testing.T) {
	// A race on the partition maps can hand one tenant another's chunk ids.
	// This runs both tenants' queries concurrently and asserts every hit
	// carries the right owner, which is the observable form of that race.
	corpus, ix, ki := seedTwoTenants(t)
	_, _, _ = corpus, ix, ki

	var wg sync.WaitGroup
	violations := make(chan string, 64)
	for _, owner := range []string{"tenant-a", "tenant-b"} {
		wg.Add(1)
		go func(owner string) {
			defer wg.Done()
			for i := 0; i < 200; i++ {
				hits, err := retrieval.HybridQuery(ix, ki, owner, "quarterly revenue targets", 5, retrieval.DefaultHybridParams())
				if err != nil {
					violations <- owner + ": error " + err.Error()
					return
				}
				for _, h := range hits {
					if h.Owner != owner {
						violations <- owner + " received " + h.Owner
						return
					}
				}
			}
		}(owner)
	}
	wg.Wait()
	close(violations)

	for v := range violations {
		t.Fatalf("cross-tenant result under concurrency: %s", v)
	}
}

func TestThePartitionIsTheSearchKeyNotAPostFilter(t *testing.T) {
	// Documents the invariant rather than the outcome: a partition that
	// contains the other owner's chunk ids would pass a post-filter test and
	// still be a leak. The scoping must be structural.
	corpus, _, _ := seedTwoTenants(t)

	scopedA := corpus.Scoped("tenant-a")
	if len(scopedA) != 1 {
		t.Fatalf("tenant-a's partition has %d chunks", len(scopedA))
	}
	foreignChunk := retrieval.ChunkID(retrieval.DocumentID("tenant-b", "secret"), 0)
	for _, cid := range scopedA {
		if cid == foreignChunk {
			t.Fatal("the other tenant's chunk id is inside tenant-a's partition")
		}
	}
}
