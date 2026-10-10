// Package inference provides speculative decoding and KV-cache
// optimizations for autoregressive decoding.
package inference

import (
	"errors"
	"sync"
	"sync/atomic"
)

// SpeculativeConfig holds speculative decoding configuration.
type SpeculativeConfig struct {
	DraftLen     int // tokens drafted per step
	AcceptLen    int // max accepted tokens per step
	Temperature  float64
	UseTreeDraft bool // tree-structured speculation
	MaxTreeDepth int
}

// DefaultSpeculativeConfig returns defaults.
func DefaultSpeculativeConfig() *SpeculativeConfig {
	return &SpeculativeConfig{
		DraftLen:     4,
		AcceptLen:    4,
		Temperature:  1.0,
		UseTreeDraft: false,
		MaxTreeDepth: 4,
	}
}

// TokenProb is a token with its probability.
type TokenProb struct {
	Token int
	Prob  float64
}

// VerificationResult reports the outcome of verifying drafted tokens.
type VerificationResult struct {
	Accepted       int
	Correction     int // token that replaced the first rejected draft
	AcceptedTokens []int
}

// SpeculativeDecoder implements speculative decoding where a fast
// draft model proposes tokens that a stronger target model verifies.
type SpeculativeDecoder struct {
	config   *SpeculativeConfig
	draftFn  func(ctx interface{}, prefix []int, n int) []TokenProb
	targetFn func(ctx interface{}, prefix []int, n int) []TokenProb
	stats    SpeculativeStats
	mu       sync.Mutex
}

// SpeculativeStats tracks speculation statistics.
type SpeculativeStats struct {
	Steps       atomic.Int64
	Drafted     atomic.Int64
	Accepted    atomic.Int64
	Rejected    atomic.Int64
	TargetCalls atomic.Int64
	DraftCalls  atomic.Int64
}

// NewSpeculativeDecoder creates a decoder.
// draftFn/targetFn take an opaque context, a token prefix and a count,
// returning one candidate TokenProb per position.
func NewSpeculativeDecoder(config *SpeculativeConfig,
	draftFn func(ctx interface{}, prefix []int, n int) []TokenProb,
	targetFn func(ctx interface{}, prefix []int, n int) []TokenProb) (*SpeculativeDecoder, error) {
	if draftFn == nil || targetFn == nil {
		return nil, errors.New("draft and target functions required")
	}
	if config == nil {
		config = DefaultSpeculativeConfig()
	}
	if config.DraftLen <= 0 {
		config.DraftLen = 4
	}
	return &SpeculativeDecoder{
		config:   config,
		draftFn:  draftFn,
		targetFn: targetFn,
	}, nil
}

// DecodeStep performs one speculative step.
func (sd *SpeculativeDecoder) DecodeStep(ctx interface{}, prefix []int) ([]int, error) {
	sd.mu.Lock()
	defer sd.mu.Unlock()

	n := sd.config.DraftLen
	if n > sd.config.AcceptLen {
		n = sd.config.AcceptLen
	}

	// Draft
	drafts := sd.draftFn(ctx, prefix, n)
	if len(drafts) == 0 {
		return nil, errors.New("draft produced no tokens")
	}
	sd.stats.DraftCalls.Add(1)
	sd.stats.Drafted.Add(int64(len(drafts)))

	// Target verifies the draft (including the position after the last draft)
	extended := make([]int, 0, len(prefix)+len(drafts))
	extended = append(extended, prefix...)
	for _, d := range drafts {
		extended = append(extended, d.Token)
	}
	targets := sd.targetFn(ctx, extended, len(drafts)+1)
	sd.stats.TargetCalls.Add(1)

	if len(targets) == 0 {
		return nil, errors.New("target produced no tokens")
	}

	// Verify: accept draft[i] when the target's own argmax agrees
	out := make([]int, 0, len(drafts)+1)
	accepted := 0
	for i, d := range drafts {
		if i < len(targets) && targets[i].Token == d.Token {
			out = append(out, d.Token)
			accepted++
			continue
		}
		// Reject: emit the target's correction token and stop
		tok := d.Token
		if i < len(targets) {
			tok = targets[i].Token
		}
		out = append(out, tok)
		sd.stats.Rejected.Add(1)
		sd.stats.Accepted.Add(int64(accepted))
		sd.stats.Steps.Add(1)
		return out, nil
	}
	// All drafts accepted: append the target's bonus token
	if len(targets) > len(drafts) {
		out = append(out, targets[len(drafts)].Token)
	} else {
		out = append(out, drafts[len(drafts)-1].Token)
	}
	sd.stats.Accepted.Add(int64(accepted))
	sd.stats.Steps.Add(1)
	return out, nil
}

// Stats returns speculation statistics.
func (sd *SpeculativeDecoder) Stats() *SpeculativeStats { return &sd.stats }

// AcceptanceRate returns the fraction of drafted tokens accepted.
func (sd *SpeculativeDecoder) AcceptanceRate() float64 {
	d := sd.stats.Drafted.Load()
	if d == 0 {
		return 0
	}
	return float64(sd.stats.Accepted.Load()) / float64(d)
}

// Speedup returns the average tokens generated per target call.
func (sd *SpeculativeDecoder) Speedup() float64 {
	steps := sd.stats.Steps.Load()
	if steps == 0 {
		return 0
	}
	return float64(sd.stats.Accepted.Load()) / float64(steps)
}

// KVCache is a simple key/value cache for incremental decoding.
type KVCache struct {
	mu        sync.RWMutex
	numLayers int
	keys      [][]float64
	values    [][]float64
	positions []int
	maxLen    int
	evictions atomic.Int64
	hits      atomic.Int64
	misses    atomic.Int64
}

// NewKVCache creates a cache with capacity maxLen per layer.
func NewKVCache(numLayers int, maxLen int) *KVCache {
	return &KVCache{
		numLayers: numLayers,
		keys:      make([][]float64, numLayers),
		values:    make([][]float64, numLayers),
		positions: make([]int, numLayers),
		maxLen:    maxLen,
	}
}

// Get returns the cached keys/values for a layer.
func (c *KVCache) Get(layer int) ([]float64, []float64, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	if layer < 0 || layer >= c.numLayers {
		return nil, nil, false
	}
	if len(c.keys[layer]) == 0 {
		c.misses.Add(1)
		return nil, nil, false
	}
	c.hits.Add(1)
	return c.keys[layer], c.values[layer], true
}

// Put stores keys/values for a layer, evicting the oldest when full.
func (c *KVCache) Put(layer int, k, v []float64) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if layer < 0 || layer >= c.numLayers {
		return
	}
	kv := make([]float64, len(k))
	copy(kv, k)
	vv := make([]float64, len(v))
	copy(vv, v)
	c.keys[layer] = kv
	c.values[layer] = vv
	c.positions[layer]++
	// Evict oldest entries, keeping at most maxLen. Both slices are
	// truncated independently so a short value slice cannot underflow.
	if c.maxLen > 0 {
		if len(kv) > c.maxLen {
			c.keys[layer] = kv[len(kv)-c.maxLen:]
		}
		if len(vv) > c.maxLen {
			c.values[layer] = vv[len(vv)-c.maxLen:]
		}
		c.evictions.Add(1)
	}
}

// Clear resets the cache.
func (c *KVCache) Clear() {
	c.mu.Lock()
	defer c.mu.Unlock()
	for i := range c.keys {
		c.keys[i] = nil
		c.values[i] = nil
		c.positions[i] = 0
	}
}

// Stats returns cache statistics.
func (c *KVCache) Stats() (hits, misses, evictions int64) {
	return c.hits.Load(), c.misses.Load(), c.evictions.Load()
}

// HitRate returns the fraction of cache hits.
func (c *KVCache) HitRate() float64 {
	h := c.hits.Load()
	m := c.misses.Load()
	if h+m == 0 {
		return 0
	}
	return float64(h) / float64(h+m)
}

// SlidingWindowKVCache evicts the oldest entries when full.
type SlidingWindowKVCache struct {
	*KVCache
	window int
}

// NewSlidingWindowKVCache creates a sliding window cache.
func NewSlidingWindowKVCache(numLayers, maxLen, window int) *SlidingWindowKVCache {
	if window > maxLen {
		window = maxLen
	}
	if window <= 0 {
		window = maxLen
	}
	return &SlidingWindowKVCache{
		KVCache: NewKVCache(numLayers, maxLen),
		window:  window,
	}
}

// Window returns the sliding window size.
func (c *SlidingWindowKVCache) Window() int { return c.window }

// PagedKVCache implements block-based KV allocation.
type PagedKVCache struct {
	mu         sync.RWMutex
	blockSize  int
	numBlocks  int
	freeBlocks []int
	pageTable  map[int][]int // sequence -> block ids
	evictions  atomic.Int64
}

// NewPagedKVCache creates a paged cache.
func NewPagedKVCache(blockSize, numBlocks int) *PagedKVCache {
	free := make([]int, numBlocks)
	for i := range free {
		free[i] = i
	}
	return &PagedKVCache{
		blockSize:  blockSize,
		numBlocks:  numBlocks,
		freeBlocks: free,
		pageTable:  make(map[int][]int),
	}
}

// AllocateBlocks allocates n blocks for a sequence.
func (p *PagedKVCache) AllocateBlocks(seqID, n int) ([]int, error) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if len(p.freeBlocks) < n {
		return nil, errors.New("out of KV cache blocks")
	}
	blocks := append([]int(nil), p.freeBlocks[:n]...)
	p.freeBlocks = p.freeBlocks[n:]
	p.pageTable[seqID] = append(p.pageTable[seqID], blocks...)
	return blocks, nil
}

// FreeBlocks returns a sequence's blocks to the free list.
func (p *PagedKVCache) FreeBlocks(seqID int) {
	p.mu.Lock()
	defer p.mu.Unlock()
	blocks, ok := p.pageTable[seqID]
	if !ok {
		return
	}
	p.freeBlocks = append(p.freeBlocks, blocks...)
	delete(p.pageTable, seqID)
	p.evictions.Add(int64(len(blocks)))
}

// FreeBlocks returns the number of free blocks.
func (p *PagedKVCache) FreeBlockCount() int {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return len(p.freeBlocks)
}

// Utilization returns the fraction of blocks in use.
func (p *PagedKVCache) Utilization() float64 {
	p.mu.RLock()
	defer p.mu.RUnlock()
	used := p.numBlocks - len(p.freeBlocks)
	return float64(used) / float64(p.numBlocks)
}
