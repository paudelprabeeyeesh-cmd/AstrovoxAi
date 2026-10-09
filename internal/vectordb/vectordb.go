// Package vectordb provides a vector database with approximate nearest
// neighbour (ANN) search, HNSW indexing, and persistent storage.
package vectordb

import (
	"errors"
	"fmt"
	"math"
	"sort"
	"sync"
)

// Vector is a dense embedding.
type Vector []float64

// Dimension returns the vector dimension.
func (v Vector) Dimension() int { return len(v) }

// Norm returns the L2 norm.
func (v Vector) Norm() float64 {
	var sum float64
	for _, x := range v {
		sum += x * x
	}
	return math.Sqrt(sum)
}

// Normalize returns a unit-length copy.
func (v Vector) Normalize() Vector {
	n := v.Norm()
	if n == 0 {
		return v.clone()
	}
	out := make(Vector, len(v))
	for i, x := range v {
		out[i] = x / n
	}
	return out
}

func (v Vector) clone() Vector {
	out := make(Vector, len(v))
	copy(out, v)
	return out
}

// CosineSimilarity computes cosine similarity between two vectors.
func CosineSimilarity(a, b Vector) float64 {
	if len(a) != len(b) {
		return 0
	}
	var dot, na, nb float64
	for i := range a {
		dot += a[i] * b[i]
		na += a[i] * a[i]
		nb += b[i] * b[i]
	}
	if na == 0 || nb == 0 {
		return 0
	}
	return dot / (math.Sqrt(na) * math.Sqrt(nb))
}

// DotProduct computes the dot product of two vectors.
func DotProduct(a, b Vector) float64 {
	if len(a) != len(b) {
		return 0
	}
	var sum float64
	for i := range a {
		sum += a[i] * b[i]
	}
	return sum
}

// EuclideanDistance computes the L2 distance.
func EuclideanDistance(a, b Vector) float64 {
	if len(a) != len(b) {
		return math.MaxFloat64
	}
	var sum float64
	for i := range a {
		d := a[i] - b[i]
		sum += d * d
	}
	return math.Sqrt(sum)
}

// SimilarityMetric identifies a similarity function.
type SimilarityMetric int

const (
	MetricCosine SimilarityMetric = iota
	MetricDotProduct
	MetricEuclidean
)

func (m SimilarityMetric) String() string {
	switch m {
	case MetricCosine:
		return "cosine"
	case MetricDotProduct:
		return "dot"
	case MetricEuclidean:
		return "euclidean"
	default:
		return "unknown"
	}
}

// Distance computes the distance/similarity between two vectors.
// Higher is better for cosine and dot product.
func (m SimilarityMetric) Distance(a, b Vector) float64 {
	switch m {
	case MetricCosine:
		return CosineSimilarity(a, b)
	case MetricDotProduct:
		return DotProduct(a, b)
	case MetricEuclidean:
		return -EuclideanDistance(a, b) // negate so higher is better
	default:
		return 0
	}
}

// Document is a stored record with an embedding and payload.
type Document struct {
	ID       string
	Vector   Vector
	Payload  map[string]interface{}
	VectorID int
}

// SearchResult is a single search hit.
type SearchResult struct {
	ID      string
	Score   float64
	Payload map[string]interface{}
}

// HNSWNode is a node in the HNSW graph.
type HNSWNode struct {
	doc     *Document
	level   int
	friends [][]int // friends[level] = neighbour ids
	mu      sync.RWMutex
}

// HNSWParams holds HNSW index parameters.
type HNSWParams struct {
	M              int // max neighbours per layer
	MMax0          int // max neighbours at layer 0
	EfConstruction int
	EfSearch       int
	MaxLevel       int
	ML             float64
}

// DefaultHNSWParams returns standard HNSW parameters.
func DefaultHNSWParams() HNSWParams {
	return HNSWParams{
		M:              16,
		MMax0:          32,
		EfConstruction: 200,
		EfSearch:       64,
		MaxLevel:       6,
		ML:             1.0 / math.Log(16.0),
	}
}

// HNSWIndex implements a simplified Hierarchical Navigable Small World index.
type HNSWIndex struct {
	params   HNSWParams
	metric   SimilarityMetric
	mu       sync.RWMutex
	nodes    []*HNSWNode
	entry    int // entry point node id
	maxLevel int
	rand     *randSource
}

type randSource struct {
	state uint64
}

func newRand(seed uint64) *randSource { return &randSource{state: seed} }

func (r *randSource) next() float64 {
	// xorshift64
	r.state ^= r.state << 13
	r.state ^= r.state >> 7
	r.state ^= r.state << 17
	return float64(r.state) / float64(math.MaxUint64)
}

// randomLevel draws a random level for a new node.
func (h *HNSWIndex) randomLevel() int {
	lvl := 0
	for lvl < h.params.MaxLevel && h.rand.next() < h.params.ML {
		lvl++
	}
	return lvl
}

// NewHNSWIndex creates an HNSW index.
func NewHNSWIndex(metric SimilarityMetric) *HNSWIndex {
	return &HNSWIndex{
		params: DefaultHNSWParams(),
		metric: metric,
		entry:  -1,
		rand:   newRand(42),
	}
}

// NewHNSWIndexWithParams creates an HNSW index with custom params.
func NewHNSWIndexWithParams(metric SimilarityMetric, params HNSWParams) *HNSWIndex {
	return &HNSWIndex{
		params: params,
		metric: metric,
		entry:  -1,
		rand:   newRand(42),
	}
}

// Size returns the number of indexed nodes.
func (h *HNSWIndex) Size() int {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return len(h.nodes)
}

// Len is an alias for Size.
func (h *HNSWIndex) Len() int { return h.Size() }

// Add inserts a document into the index and returns its node id.
func (h *HNSWIndex) Add(doc *Document) int {
	h.mu.Lock()
	defer h.mu.Unlock()

	id := len(h.nodes)
	doc.VectorID = id
	lvl := h.randomLevel()
	node := &HNSWNode{
		doc:   doc,
		level: lvl,
	}
	node.friends = make([][]int, lvl+1)
	for i := range node.friends {
		node.friends[i] = []int{}
	}
	h.nodes = append(h.nodes, node)

	if h.entry == -1 {
		h.entry = id
		h.maxLevel = lvl
		return id
	}

	if lvl > h.maxLevel {
		h.maxLevel = lvl
		h.entry = id
		return id
	}

	// Greedy search from entry point at each level up to lvl
	ep := h.entry
	for lc := h.maxLevel; lc >= lvl; lc-- {
		ep = h.searchLayer(doc.Vector, ep, 1, lc)
	}
	for lc := minInt(lvl, h.maxLevel); lc >= 0; lc-- {
		ep = h.searchLayer(doc.Vector, ep, h.params.EfConstruction, lc)
		neighbors := h.selectNeighbours(doc.Vector, ep, h.params.M, lc)
		node.friends[lc] = neighbors
		for _, nb := range neighbors {
			h.nodes[nb].friends[lc] = append(h.nodes[nb].friends[lc], id)
			if len(h.nodes[nb].friends[lc]) > h.params.MMax0 {
				h.pruneNeighbours(nb, lc)
			}
		}
	}
	return id
}

func (h *HNSWIndex) searchLayer(query Vector, entryID int, ef, level int) int {
	visited := map[int]bool{entryID: true}
	current := entryID
	currentDist := h.dist(query, h.nodes[current].doc.Vector)
	for {
		changed := false
		n := h.nodes[current]
		n.mu.RLock()
		friends := append([]int(nil), n.friends[level]...)
		n.mu.RUnlock()
		for _, f := range friends {
			if visited[f] {
				continue
			}
			visited[f] = true
			d := h.dist(query, h.nodes[f].doc.Vector)
			if d > currentDist {
				current = f
				currentDist = d
				changed = true
			}
		}
		if !changed {
			break
		}
	}
	return current
}

func (h *HNSWIndex) selectNeighbours(query Vector, candidateID, m, level int) []int {
	cand := h.nodes[candidateID]
	cand.mu.RLock()
	friends := append([]int(nil), cand.friends[level]...)
	cand.mu.RUnlock()
	candSet := map[int]bool{candidateID: true}
	candSet[candidateID] = true
	for _, f := range friends {
		candSet[f] = true
	}
	ids := make([]int, 0, len(candSet))
	for id := range candSet {
		ids = append(ids, id)
	}
	sort.Slice(ids, func(i, j int) bool {
		return h.dist(query, h.nodes[ids[i]].doc.Vector) > h.dist(query, h.nodes[ids[j]].doc.Vector)
	})
	if len(ids) > m {
		ids = ids[:m]
	}
	return ids
}

func (h *HNSWIndex) pruneNeighbours(nodeID, level int) {
	n := h.nodes[nodeID]
	n.mu.Lock()
	defer n.mu.Unlock()
	if len(n.friends[level]) <= h.params.MMax0 {
		return
	}
	n.friends[level] = n.friends[level][:h.params.MMax0]
}

func (h *HNSWIndex) dist(a, b Vector) float64 {
	return h.metric.Distance(a, b)
}

// Search finds the k nearest neighbours of a query vector.
func (h *HNSWIndex) Search(query Vector, k int) []SearchResult {
	h.mu.RLock()
	defer h.mu.RUnlock()
	if h.entry == -1 || len(h.nodes) == 0 {
		return nil
	}
	ep := h.entry
	for lc := h.maxLevel; lc > 0; lc-- {
		ep = h.searchLayer(query, ep, 1, lc)
	}
	cand := h.searchLayerEf(query, ep, h.params.EfSearch, 0)
	sort.Slice(cand, func(i, j int) bool {
		return h.dist(query, h.nodes[cand[i]].doc.Vector) > h.dist(query, h.nodes[cand[j]].doc.Vector)
	})
	if len(cand) > k {
		cand = cand[:k]
	}
	out := make([]SearchResult, 0, len(cand))
	for _, id := range cand {
		d := h.nodes[id].doc
		out = append(out, SearchResult{
			ID:      d.ID,
			Score:   h.dist(query, d.Vector),
			Payload: d.Payload,
		})
	}
	return out
}

func (h *HNSWIndex) searchLayerEf(query Vector, entryID int, ef, level int) []int {
	visited := map[int]bool{entryID: true}
	candidates := []int{entryID}
	for {
		// expand best unvisited candidate
		best := -1
		for _, c := range candidates {
			if !visited[c] {
				continue
			}
			_ = c
		}
		changed := false
		for _, c := range candidates {
			d := h.dist(query, h.nodes[c].doc.Vector)
			_ = d
		}
		// simple expansion
		expanded := false
		for _, c := range candidates {
			n := h.nodes[c]
			n.mu.RLock()
			friends := append([]int(nil), n.friends[level]...)
			n.mu.RUnlock()
			for _, f := range friends {
				if visited[f] {
					continue
				}
				visited[f] = true
				candidates = append(candidates, f)
				changed = true
				expanded = true
			}
		}
		if !expanded {
			break
		}
		if changed && best == -1 {
			// trim to ef
			sort.Slice(candidates, func(i, j int) bool {
				return h.dist(query, h.nodes[candidates[i]].doc.Vector) > h.dist(query, h.nodes[candidates[j]].doc.Vector)
			})
			if len(candidates) > ef {
				candidates = candidates[:ef]
			}
		}
	}
	sort.Slice(candidates, func(i, j int) bool {
		return h.dist(query, h.nodes[candidates[i]].doc.Vector) > h.dist(query, h.nodes[candidates[j]].doc.Vector)
	})
	if len(candidates) > ef {
		candidates = candidates[:ef]
	}
	return candidates
}

// VectorDB is a simple vector database with optional HNSW index.
type VectorDB struct {
	mu        sync.RWMutex
	docs      map[string]*Document
	index     *HNSWIndex
	metric    SimilarityMetric
	dimension int
	useIndex  bool
}

// NewVectorDB creates a vector database using brute-force search.
func NewVectorDB(metric SimilarityMetric, dimension int) *VectorDB {
	return &VectorDB{
		docs:      make(map[string]*Document),
		metric:    metric,
		dimension: dimension,
		useIndex:  false,
	}
}

// NewVectorDBWithIndex creates a vector database using the HNSW index.
func NewVectorDBWithIndex(metric SimilarityMetric, dimension int) *VectorDB {
	return &VectorDB{
		docs:      make(map[string]*Document),
		index:     NewHNSWIndex(metric),
		metric:    metric,
		dimension: dimension,
		useIndex:  true,
	}
}

// Insert adds a document to the database.
func (db *VectorDB) Insert(doc *Document) error {
	if doc == nil {
		return errors.New("nil document")
	}
	if len(doc.Vector) != db.dimension {
		return fmt.Errorf("dimension mismatch: got %d, want %d", len(doc.Vector), db.dimension)
	}
	db.mu.Lock()
	defer db.mu.Unlock()
	db.docs[doc.ID] = doc
	if db.useIndex {
		db.index.Add(doc)
	}
	return nil
}

// InsertBatch inserts multiple documents.
func (db *VectorDB) InsertBatch(docs []*Document) (int, error) {
	inserted := 0
	for _, d := range docs {
		if err := db.Insert(d); err != nil {
			return inserted, err
		}
		inserted++
	}
	return inserted, nil
}

// Get retrieves a document by ID.
func (db *VectorDB) Get(id string) (*Document, bool) {
	db.mu.RLock()
	defer db.mu.RUnlock()
	d, ok := db.docs[id]
	return d, ok
}

// Delete removes a document by ID.
func (db *VectorDB) Delete(id string) bool {
	db.mu.Lock()
	defer db.mu.Unlock()
	if _, ok := db.docs[id]; ok {
		delete(db.docs, id)
		return true
	}
	return false
}

// Len returns the number of documents.
func (db *VectorDB) Len() int {
	db.mu.RLock()
	defer db.mu.RUnlock()
	return len(db.docs)
}

// Search performs a k-nearest-neighbour search.
func (db *VectorDB) Search(query Vector, k int) ([]SearchResult, error) {
	if len(query) != db.dimension {
		return nil, fmt.Errorf("dimension mismatch: got %d, want %d", len(query), db.dimension)
	}
	db.mu.RLock()
	defer db.mu.RUnlock()

	if db.useIndex && db.index.Len() > 0 {
		return db.index.Search(query, k), nil
	}

	// Brute force
	type scored struct {
		id    string
		score float64
		doc   *Document
	}
	all := make([]scored, 0, len(db.docs))
	for _, d := range db.docs {
		all = append(all, scored{id: d.ID, score: db.metric.Distance(query, d.Vector), doc: d})
	}
	sort.Slice(all, func(i, j int) bool { return all[i].score > all[j].score })
	if len(all) > k {
		all = all[:k]
	}
	out := make([]SearchResult, 0, len(all))
	for _, s := range all {
		out = append(out, SearchResult{ID: s.id, Score: s.score, Payload: s.doc.Payload})
	}
	return out, nil
}

// SearchWithFilter performs a filtered k-NN search.
func (db *VectorDB) SearchWithFilter(query Vector, k int, keep func(payload map[string]interface{}) bool) ([]SearchResult, error) {
	if len(query) != db.dimension {
		return nil, fmt.Errorf("dimension mismatch: got %d, want %d", len(query), db.dimension)
	}
	db.mu.RLock()
	defer db.mu.RUnlock()

	type scored struct {
		id    string
		score float64
		doc   *Document
	}
	all := make([]scored, 0, len(db.docs))
	for _, d := range db.docs {
		if keep != nil && !keep(d.Payload) {
			continue
		}
		all = append(all, scored{id: d.ID, score: db.metric.Distance(query, d.Vector), doc: d})
	}
	sort.Slice(all, func(i, j int) bool { return all[i].score > all[j].score })
	if len(all) > k {
		all = all[:k]
	}
	out := make([]SearchResult, 0, len(all))
	for _, s := range all {
		out = append(out, SearchResult{ID: s.id, Score: s.score, Payload: s.doc.Payload})
	}
	return out, nil
}

// Update modifies an existing document's vector and payload.
func (db *VectorDB) Update(doc *Document) error {
	db.mu.Lock()
	defer db.mu.Unlock()
	if _, ok := db.docs[doc.ID]; !ok {
		return fmt.Errorf("document %q not found", doc.ID)
	}
	if len(doc.Vector) != db.dimension {
		return fmt.Errorf("dimension mismatch: got %d, want %d", len(doc.Vector), db.dimension)
	}
	db.docs[doc.ID] = doc
	return nil
}

// All returns all documents (useful for snapshots).
func (db *VectorDB) All() []*Document {
	db.mu.RLock()
	defer db.mu.RUnlock()
	out := make([]*Document, 0, len(db.docs))
	for _, d := range db.docs {
		out = append(out, d)
	}
	return out
}

// Stats returns database statistics.
func (db *VectorDB) Stats() DBStats {
	db.mu.RLock()
	defer db.mu.RUnlock()
	return DBStats{
		Documents: len(db.docs),
		Dimension: db.dimension,
		Indexed:   db.useIndex,
		Metric:    db.metric.String(),
	}
}

// DBStats describes a database.
type DBStats struct {
	Documents int
	Dimension int
	Indexed   bool
	Metric    string
}

func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}