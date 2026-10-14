package evals

import (
	"fmt"
	"math/rand"
	"strings"
	"testing"

	"github.com/astrovox/astrovox/internal/retrieval"
)

// A 10-document fixture cannot show what recall@k means. Every answer is in the
// top two at that size, so recall@5 and recall@50 are indistinguishable and the
// metric is decorative.
//
// This builds a corpus large enough for the cutoff to matter, with generation
// seeded so a run is reproducible. Relevance is structural: each question names
// exactly one document's terms plus shared filler, so the label is right by
// construction rather than by judgement - which also means it only measures
// retrieval, not annotation quality.

const (
	corpusDocs   = 200
	sharedFiller = "the system processes requests in order and every component reports its status through the same channel"
)

// buildLargeCorpus generates docs with a stable vocabulary.
func buildLargeCorpus(rng *rand.Rand) (corpus *retrieval.Corpus, ix *retrieval.Index, ki *retrieval.KeywordIndex, titles []string) {
	corpus = retrieval.NewCorpus()
	ix = retrieval.NewIndex(corpus, retrieval.NewHashEmbeddable(64))
	ki = retrieval.NewKeywordIndex(corpus)

	titles = make([]string, 0, corpusDocs)
	for i := 0; i < corpusDocs; i++ {
		// Distinctive terms are drawn from an indexed vocabulary rather than
		// sampled from a small word list. The first version sampled 8 adjectives
		// against 8 nouns, which yields 64 distinct pairs for 200 documents, so a
		// third of the corpus shared its identifying terms and the retrieval
		// legitimately returned a different document with the same terms. The
		// corpus was ambiguous, not the search wrong.
		a := fmt.Sprintf("zone%02d", i%40)
		n := fmt.Sprintf("sphere%03d", i)
		title := fmt.Sprintf("doc-%04d-%s-%s", i, a, n)
		titles = append(titles, title)

		distinctive := []string{a, n}
		text := strings.Join(distinctive, " ") + " " + sharedFiller
		docID := retrieval.DocumentID("eval", title)
		corpus.AddDocument(&retrieval.Document{
			ID: docID, Owner: "eval", Tenant: "eval", Title: title,
		})
		span := retrieval.ChunkText(text, retrieval.ChunkParams{Size: 512, Overlap: 0})[0]
		cid := retrieval.ChunkID(docID, 0)
		corpus.AddChunk(&retrieval.Chunk{
			ID: cid, DocumentID: docID, Owner: "eval", Tenant: "eval",
			Position: 0, Text: span,
		})
		_ = ix.EmbedChunk(cid, span)
		ki.AddChunk(cid, span)
	}
	return corpus, ix, ki, titles
}

func largeSet(titles []string) Set {
	// Twenty questions, each naming its own document's distinctive terms plus
	// filler words that appear in all 200 docs. The filler is the point: it
	// makes BM25's length normalisation and IDF do real work rather than
	// trivially separating the documents.
	queries := make([]Query, 0, 20)
	for i := 0; i < 20; i++ {
		title := titles[i*corpusDocs/20]
		a := fmt.Sprintf("zone%02d", (i*corpusDocs/20)%40)
		n := fmt.Sprintf("sphere%03d", i*corpusDocs/20)
		text := "what does the " + a + " " + n +
			" system report through the shared channel"
		queries = append(queries, Query{
			ID:   title,
			Text: text,
			// Permits names the owner. Run defaults an empty one to
			// "eval-owner", and a corpus ingested under a different owner is
			// invisible to it - which is a well-behaved ACL doing exactly what
			// it should, and a fixture that silently measures nothing.
			Permits:  "eval",
			Relevant: []string{retrieval.ChunkID(retrieval.DocumentID("eval", title), 0)},
		})
	}
	return Set{Name: "large-corpus", Queries: queries}
}

func TestRecallAtKOnALargeCorpus(t *testing.T) {
	rng := rand.New(rand.NewSource(7))
	_, ix, ki, titles := buildLargeCorpus(rng)
	set := largeSet(titles)
	adapter := RetrievalAdapter{
		Index: ix, Keyword: ki, Params: retrieval.DefaultHybridParams(),
	}

	// Cutoffs chosen so the difference is visible: 1 is exact top-1, 5 is a
	// shortlist, 50 is a quarter of the corpus.
	for _, k := range []int{1, 5, 20, 50} {
		report, err := Run(set, adapter, k)
		if err != nil {
			t.Fatalf("eval at k=%d failed: %v", k, err)
		}
		t.Logf("k=%-3d recall@k=%.3f mrr=%.3f ndcg@k=%.3f misses=%d",
			k, report.MeanRecallAtK, report.MeanMRR, report.MeanNDCGAtK, len(report.Misses))
	}
}

func TestRecallMonotonicallyImprovesWithTheCutoff(t *testing.T) {
	// A larger cutoff can only retrieve more of the relevant set, so recall can
	// only stay flat or rise. If it falls, the retrieval is not deterministic or
	// the metric is wrong - and this assertion is cheaper than trusting either.
	rng := rand.New(rand.NewSource(11))
	_, ix, ki, titles := buildLargeCorpus(rng)
	set := largeSet(titles)
	adapter := RetrievalAdapter{
		Index: ix, Keyword: ki, Params: retrieval.DefaultHybridParams(),
	}

	previous := -1.0
	for _, k := range []int{1, 2, 5, 10, 20, 50, 100} {
		report, err := Run(set, adapter, k)
		if err != nil {
			t.Fatalf("eval at k=%d failed: %v", k, err)
		}
		if report.MeanRecallAtK < previous {
			t.Fatalf("recall fell from %.3f to %.3f when k rose to %d",
				previous, report.MeanRecallAtK, k)
		}
		previous = report.MeanRecallAtK
	}
	if previous < 1.0 {
		t.Fatalf("recall never reached 1.000 even at k=100; best was %.3f", previous)
	}
}

func TestTheLargeCorpusIsActuallyLarge(t *testing.T) {
	// A guard on the fixture itself. If generation silently produced a handful
	// of documents, every measurement above would still pass while proving
	// nothing about scale.
	rng := rand.New(rand.NewSource(3))
	corpus, _, _, titles := buildLargeCorpus(rng)
	if got := len(corpus.Documents("eval")); got != corpusDocs {
		t.Fatalf("corpus has %d documents, want %d", got, corpusDocs)
	}
	if len(titles) != corpusDocs {
		t.Fatalf("%d titles, want %d", len(titles), corpusDocs)
	}
}

func TestTheFillerIsDistributedAcrossTheCorpus(t *testing.T) {
	// The shared filler must appear in every document, or it is not a filler and
	// the corpus does not exercise length normalisation.
	rng := rand.New(rand.NewSource(5))
	corpus, _, ki, _ := buildLargeCorpus(rng)
	_ = corpus

	hits := ki.Search("eval", "component reports its status", corpusDocs)
	withFiller := 0
	for _, hit := range hits {
		if strings.Contains(hit.Text, "reports its status") {
			withFiller++
		}
	}
	if withFiller != corpusDocs {
		t.Fatalf("only %d of %d documents contain the filler", withFiller, corpusDocs)
	}
}
