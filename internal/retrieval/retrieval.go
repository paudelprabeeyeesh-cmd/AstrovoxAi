// Package retrieval implements retrieval-augmented generation in Go:
// ingest, chunk, embed, index, and query, with access control applied
// inside the query rather than filtered out of its results.
//
// The distinction is the entire reason this package is hard. Retrieval is
// the one path where a caller can influence what context reaches the model,
// so an ACL applied after the recall - "run the search, then drop the rows
// the caller may not see" - leaks in three ways that are all observable:
//
//  1. It wastes budget scoring documents the caller will never see.
//  2. It changes per-tenant recall, so one tenant's index looks smaller
//     than it is and a result that would have been top-k is missing.
//  3. Worst, it is one forgotten filter away from a cross-tenant read, and
//     the failure is silent because the filter is the last step.
//
// So the index is partitioned by owner and the owner is part of the search
// key. A query that omits it returns nothing rather than everything.
//
// Citation is carried end to end: a chunk remembers the document and the
// position it came from, and the answer's claim maps back to it. An answer
// whose only support is a chunk the caller may not read is refused, not
// rendered without its citation.
package retrieval

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"sort"
	"sync"
	"time"
)

// Document is an ingested source.
type Document struct {
	ID     string `json:"id"`
	Owner  string `json:"owner"`
	Tenant string `json:"tenant"`
	Title  string `json:"title"`
	// MediaType is the declared type, used for preview routing.
	MediaType string    `json:"media_type,omitempty"`
	CreatedAt time.Time `json:"created_at"`
}

// Chunk is a retrievable span of a document.
type Chunk struct {
	ID         string `json:"id"`
	DocumentID string `json:"document_id"`
	// Owner and Tenant denormalised onto the chunk, so the index can scope
	// by owner without a join. This is what makes the ACL part of the query
	// key rather than a post-filter.
	Owner  string `json:"owner"`
	Tenant string `json:"tenant"`
	// Position is the span's offset in the document, so a citation can point
	// at where in the source a claim came from.
	Position  int       `json:"position"`
	Text      string    `json:"text"`
	CreatedAt time.Time `json:"created_at"`
}

// Vector is an embedded chunk.
type Vector struct {
	ChunkID   string    `json:"chunk_id"`
	Owner     string    `json:"owner"`
	Tenant    string    `json:"tenant"`
	Embedding []float32 `json:"embedding"`
	// Model identifies what produced the embedding, so an index can never
	// mix embeddings from different models and return nonsense.
	Model string `json:"model"`
}

// Embedder produces a vector for a piece of text.
type Embedder interface {
	// Embed returns a fixed-length vector for text.
	Embed(text string) []float32
	// Model names the model, so the index can reject a mixed set.
	Model() string
}

// Corpus is the indexed set, partitioned by owner.
//
// Partitioning by owner is the access control. A query carries the owner,
// and the index searches only that owner's partition, so a document from
// another owner is never scored rather than scored and dropped.
type Corpus struct {
	mu sync.RWMutex

	documents map[string]*Document
	chunks    map[string]*Chunk
	// byOwner is the partition: owner -> chunk ids. Search scopes to this
	// before scoring anything.
	byOwner map[string]map[string]bool

	nextID int
}

// NewCorpus returns an empty corpus.
func NewCorpus() *Corpus {
	return &Corpus{
		documents: map[string]*Document{},
		chunks:    map[string]*Chunk{},
		byOwner:   map[string]map[string]bool{},
	}
}

// AddDocument registers a document in an owner's partition.
func (c *Corpus) AddDocument(d *Document) *Document {
	c.mu.Lock()
	defer c.mu.Unlock()
	if d.CreatedAt.IsZero() {
		d.CreatedAt = time.Now().UTC()
	}
	c.documents[d.ID] = d
	partition := c.byOwner[d.Owner]
	if partition == nil {
		partition = map[string]bool{}
		c.byOwner[d.Owner] = partition
	}
	return d
}

// AddChunk registers a chunk in its owner's partition.
func (c *Corpus) AddChunk(k *Chunk) *Chunk {
	c.mu.Lock()
	defer c.mu.Unlock()
	if k.CreatedAt.IsZero() {
		k.CreatedAt = time.Now().UTC()
	}
	doc := c.documents[k.DocumentID]
	if doc != nil {
		// Owner and tenant are taken from the document, never from the
		// caller's request: a chunk inherits its document's scope.
		k.Owner = doc.Owner
		k.Tenant = doc.Tenant
	}
	c.chunks[k.ID] = k
	partition := c.byOwner[k.Owner]
	if partition == nil {
		partition = map[string]bool{}
		c.byOwner[k.Owner] = partition
	}
	partition[k.ID] = true
	return k
}

// Document returns a document, scoped to the owner.
func (c *Corpus) Document(owner, id string) *Document {
	c.mu.RLock()
	defer c.mu.RUnlock()
	d := c.documents[id]
	if d == nil || d.Owner != owner {
		return nil
	}
	out := *d
	return &out
}

// Documents returns the owner's documents.
func (c *Corpus) Documents(owner string) []*Document {
	c.mu.RLock()
	defer c.mu.RUnlock()
	var out []*Document
	for _, d := range c.documents {
		if d.Owner == owner {
			out = append(out, d)
		}
	}
	// Stable order, so a listing is reproducible between two identical calls.
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out
}

// ChunksOf returns the owner's chunks for a document.
func (c *Corpus) ChunksOf(owner, documentID string) []*Chunk {
	c.mu.RLock()
	defer c.mu.RUnlock()
	var out []*Chunk
	for _, k := range c.chunks {
		if k.Owner == owner && k.DocumentID == documentID {
			out = append(out, k)
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Position < out[j].Position })
	return out
}

// Scoped returns the chunk ids visible to an owner. This is the search key,
// and an unknown owner genuinely has no visible chunks rather than all of
// them.
func (c *Corpus) Scoped(owner string) []string {
	c.mu.RLock()
	defer c.mu.RUnlock()
	partition := c.byOwner[owner]
	out := make([]string, 0, len(partition))
	for id := range partition {
		out = append(out, id)
	}
	// Deterministic, so a tie in score is broken the same way every run.
	sort.Strings(out)
	return out
}

// DeleteDocument removes a document and its chunks from the owner's
// partition, owner-scoped. A cross-owner delete is a no-op rather than a
// cascade.
func (c *Corpus) DeleteDocument(owner, id string) bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	d := c.documents[id]
	if d == nil || d.Owner != owner {
		return false
	}
	delete(c.documents, id)
	for cid, k := range c.chunks {
		if k.DocumentID == id {
			delete(c.chunks, cid)
			delete(c.byOwner[owner], cid)
		}
	}
	return true
}

// ---------------------------------------------------------------------------
// Chunking
// ---------------------------------------------------------------------------

// ChunkParams controls splitting.
type ChunkParams struct {
	// Size is the target chunk length in characters.
	Size int
	// Overlap is the number of characters adjacent chunks share, so a claim
	// spanning a boundary is still retrievable.
	Overlap int
}

// DefaultChunkParams returns a workable default. Overlap is a third of the
// size, which keeps a boundary claim reachable without duplicating a third
// of the text.
func DefaultChunkParams() ChunkParams {
	return ChunkParams{Size: 512, Overlap: 170}
}

// ChunkText splits text into overlapping spans. It splits on a boundary
// when one is available rather than at a fixed offset, because a chunk cut
// mid-word is unreachable by a keyword search for that word.
func ChunkText(text string, p ChunkParams) []string {
	if p.Size <= 0 {
		p.Size = DefaultChunkParams().Size
	}
	if p.Overlap < 0 {
		p.Overlap = 0
	}
	if p.Overlap >= p.Size {
		p.Overlap = p.Size / 3
	}
	runes := []rune(text)
	if len(runes) <= p.Size {
		return []string{text}
	}
	step := p.Size - p.Overlap
	var out []string
	for start := 0; start < len(runes); start += step {
		end := start + p.Size
		if end > len(runes) {
			end = len(runes)
		}
		// Prefer a whitespace boundary near the end of the span.
		cut := end
		if end < len(runes) {
			for i := end; i > start+step; i-- {
				if runes[i] == ' ' || runes[i] == '\n' {
					cut = i + 1
					break
				}
			}
		}
		out = append(out, string(runes[start:cut]))
		if cut >= len(runes) {
			break
		}
	}
	return out
}

// ---------------------------------------------------------------------------
// Embedding and search
// ---------------------------------------------------------------------------

// cosine is the similarity between two vectors. Zero-length vectors are
// zero, so an un-embedded chunk cannot outrank a real one.
func cosine(a, b []float32) float32 {
	if len(a) == 0 || len(b) == 0 {
		return 0
	}
	n := len(a)
	if len(b) < n {
		n = len(b)
	}
	var dot, na, nb float32
	for i := 0; i < n; i++ {
		dot += a[i] * b[i]
		na += a[i] * a[i]
		nb += b[i] * b[i]
	}
	if na == 0 || nb == 0 {
		return 0
	}
	return dot / (sqrt32(na) * sqrt32(nb))
}

// sqrt32 avoids a math import for one square root.
func sqrt32(v float32) float32 {
	if v <= 0 {
		return 0
	}
	// Newton-Raphson converges in a handful of steps for the magnitudes
	// involved.
	x := v
	if x > 1 {
		x /= 2
	}
	for i := 0; i < 20; i++ {
		nx := (x + v/x) / 2
		if nx == x {
			break
		}
		x = nx
	}
	return x
}

// Index holds vectors alongside the corpus, partitioned the same way.
type Index struct {
	mu     sync.RWMutex
	corpus *Corpus
	// vectors is keyed by chunk id.
	vectors map[string]*Vector
	embed   Embedder
}

// NewIndex returns an index over a corpus.
func NewIndex(corpus *Corpus, embed Embedder) *Index {
	return &Index{corpus: corpus, vectors: map[string]*Vector{}, embed: embed}
}

// EmbedChunk embeds a chunk and stores the vector.
func (ix *Index) EmbedChunk(chunkID, text string) error {
	if ix.embed == nil {
		return errNoEmbedder
	}
	ix.mu.Lock()
	defer ix.mu.Unlock()
	ix.vectors[chunkID] = &Vector{
		ChunkID:   chunkID,
		Embedding: ix.embed.Embed(text),
		Model:     ix.embed.Model(),
	}
	return nil
}

// errNoEmbedder is returned when an index is built without one.
var errNoEmbedder = errors.New("retrieval: no embedder configured")

// Hit is one search result.
type Hit struct {
	ChunkID string  `json:"chunk_id"`
	Owner   string  `json:"owner"`
	Score   float32 `json:"score"`
	Text    string  `json:"text"`
	// DocumentID and Position are the citation, carried so an answer can
	// point at where the support came from.
	DocumentID string `json:"document_id"`
	Position   int    `json:"position"`
}

// Search returns the top-k chunks in the owner's partition. The owner is the
// search key: a chunk outside the partition is never scored, so a
// cross-tenant leak is impossible by construction rather than by filter.
func (ix *Index) Search(owner string, query string, k int) ([]Hit, error) {
	if ix.embed == nil {
		return nil, errNoEmbedder
	}
	if k <= 0 {
		return nil, nil
	}
	qv := ix.embed.Embed(query)

	ix.corpus.mu.RLock()
	ix.mu.RLock()
	partition := ix.corpus.byOwner[owner]
	candidates := make([]Hit, 0, len(partition))
	for cid := range partition {
		v := ix.vectors[cid]
		if v == nil {
			// An un-embedded chunk is skipped rather than scored zero, so it
			// cannot occupy a result slot.
			continue
		}
		if v.Model != ix.embed.Model() {
			// A mixed-model index would return cosine distances between
			// incompatible spaces, so the vector is refused.
			continue
		}
		k := ix.corpus.chunks[cid]
		if k == nil {
			continue
		}
		ix.mu.RUnlock()
		candidates = append(candidates, Hit{
			ChunkID:    cid,
			Owner:      k.Owner,
			Score:      cosine(qv, v.Embedding),
			Text:       k.Text,
			DocumentID: k.DocumentID,
			Position:   k.Position,
		})
		ix.mu.RLock()
	}
	ix.mu.RUnlock()
	ix.corpus.mu.RUnlock()

	// Sort by score descending, ties broken by chunk id so the ranking is
	// deterministic between two identical queries.
	sort.Slice(candidates, func(i, j int) bool {
		if candidates[i].Score != candidates[j].Score {
			return candidates[i].Score > candidates[j].Score
		}
		return candidates[i].ChunkID < candidates[j].ChunkID
	})
	if k > len(candidates) {
		k = len(candidates)
	}
	return candidates[:k], nil
}

// ---------------------------------------------------------------------------
// Answer assembly with citation checks
// ---------------------------------------------------------------------------

// Claim is one statement in a generated answer and the chunk that supports
// it.
type Claim struct {
	// Text is the statement.
	Text string `json:"text"`
	// ChunkID is the supporting chunk. Empty means unsupported.
	ChunkID string `json:"chunk_id"`
}

// GroundedAnswer is an answer with its citations, and the verdict on
// whether each claim is actually supported.
type GroundedAnswer struct {
	Answer string  `json:"answer"`
	Claims []Claim `json:"claims"`
	// Grounded is true only when every claim has a supporting chunk the
	// caller may read.
	Grounded bool `json:"grounded"`
	// Unsupported lists the claims that could not be grounded, so the
	// failure is diagnosable rather than a bare boolean.
	Unsupported []string `json:"unsupported,omitempty"`
}

// Assemble builds a grounded answer. A claim whose chunk is not in the
// caller's partition makes the answer ungrounded rather than dropping the
// citation silently.
func Assemble(answer string, claims []Claim, ix *Index, owner string) *GroundedAnswer {
	out := &GroundedAnswer{Answer: answer, Grounded: true}
	scoped := map[string]bool{}
	for _, cid := range ix.corpus.Scoped(owner) {
		scoped[cid] = true
	}
	for _, c := range claims {
		if c.ChunkID == "" || !scoped[c.ChunkID] {
			out.Grounded = false
			out.Unsupported = append(out.Unsupported, c.Text)
			continue
		}
		out.Claims = append(out.Claims, c)
	}
	return out
}

// ---------------------------------------------------------------------------
// Ingest
// ---------------------------------------------------------------------------

// IngestResult reports what an ingest produced.
type IngestResult struct {
	DocumentID string   `json:"document_id"`
	ChunkIDs   []string `json:"chunk_ids"`
	// Rejected is set when the document was refused, with the reason.
	Rejected string `json:"rejected,omitempty"`
}

// Ingest chunks and embeds a document for an owner. It returns a rejected
// result rather than an error for a refusal, so a caller can see that the
// document was considered and why it was not stored.
//
// The document's owner is the ingest owner and nothing else: the caller
// supplies text, and the corpus derives the rest.
func Ingest(corpus *Corpus, ix *Index, owner, tenant, title, text string, params ChunkParams) *IngestResult {
	if text == "" {
		return &IngestResult{Rejected: "empty document"}
	}
	if title == "" {
		title = "untitled"
	}
	id := DocumentID(owner, title)
	corpus.AddDocument(&Document{
		ID:        id,
		Owner:     owner,
		Tenant:    tenant,
		Title:     title,
		CreatedAt: time.Now().UTC(),
	})

	res := &IngestResult{DocumentID: id}
	spans := ChunkText(text, params)
	for pos, span := range spans {
		cid := ChunkID(id, pos)
		corpus.AddChunk(&Chunk{
			ID:         cid,
			DocumentID: id,
			Owner:      owner,
			Tenant:     tenant,
			Position:   pos,
			Text:       span,
			CreatedAt:  time.Now().UTC(),
		})
		res.ChunkIDs = append(res.ChunkIDs, cid)
		if ix != nil {
			_ = ix.EmbedChunk(cid, span)
		}
	}
	return res
}

// DocumentID derives a stable document id from an owner and title, so
// re-ingesting the same document updates it rather than creating a second
// copy that a later search would rank against.
func DocumentID(owner, title string) string {
	h := sha256.Sum256([]byte(owner + "/" + title))
	return "doc_" + hex.EncodeToString(h[:8])
}

// ChunkID derives a stable chunk id from its document and position.
func ChunkID(documentID string, position int) string {
	h := sha256.Sum256([]byte(documentID + "/" + itoa(position)))
	return "chk_" + hex.EncodeToString(h[:8])
}

// itoa avoids a strconv import for one call.
func itoa(v int) string {
	if v == 0 {
		return "0"
	}
	neg := v < 0
	if neg {
		v = -v
	}
	var b [20]byte
	i := len(b)
	for v > 0 {
		i--
		b[i] = byte('0' + v%10)
		v /= 10
	}
	if neg {
		i--
		b[i] = '-'
	}
	return string(b[i:])
}
