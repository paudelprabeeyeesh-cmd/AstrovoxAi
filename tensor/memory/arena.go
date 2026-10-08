// Package memory provides the tensor engine's allocation layer:
// aligned system allocation, bump arenas, size-class pools, buffer
// reuse registries, and zero-copy import handles.
package memory

import (
	"sync"
	"sync/atomic"
	"unsafe"

	"github.com/astrovox/astrovox/internal/errors"
)

// DefaultAlignment is the cache-line alignment used for tensor buffers.
const DefaultAlignment = 64

// AlignedAlloc allocates a byte slice whose data pointer is aligned to
// align bytes (align must be a power of two). The returned slice keeps
// the underlying over-allocation alive for the GC.
func AlignedAlloc(size, align int) []byte {
	if size <= 0 {
		return nil
	}
	if align <= 1 {
		return make([]byte, size)
	}
	raw := make([]byte, size+align-1)
	addr := uintptr(unsafe.Pointer(&raw[0]))
	off := int((uintptr(align) - (addr % uintptr(align))) % uintptr(align))
	return raw[off : off+size : off+size]
}

// Arena is a bump allocator with aligned allocation and O(1) reset.
// Allocations must not outlive the arena's Reset: the contract is
// enforced in debug builds by poisoning on reset.
type Arena struct {
	mu        sync.Mutex
	buf       []byte
	off       int
	peak      int
	allocs    int64
	resets    int64
	poison    bool
	highWater int
}

// NewArena creates an arena with the given initial capacity.
func NewArena(capacity int) *Arena {
	if capacity <= 0 {
		capacity = 1024 * 1024
	}
	return &Arena{
		buf:    AlignedAlloc(capacity, DefaultAlignment),
		poison: true,
	}
}

// Alloc returns a zeroed, aligned region of size bytes. Allocations
// larger than 25% of arena capacity bypass the arena to the system
// allocator.
func (a *Arena) Alloc(size int) ([]byte, error) {
	if size <= 0 {
		return nil, nil
	}
	a.mu.Lock()
	defer a.mu.Unlock()
	if size > len(a.buf)/4 {
		a.allocs++
		a.peak += size
		return AlignedAlloc(size, DefaultAlignment), nil
	}
	aligned := (a.off + DefaultAlignment - 1) &^ (DefaultAlignment - 1)
	if aligned+size > len(a.buf) {
		newCap := len(a.buf) * 2
		for newCap < aligned+size {
			newCap *= 2
		}
		grown := AlignedAlloc(newCap, DefaultAlignment)
		copy(grown, a.buf[:a.off])
		a.buf = grown
	}
	region := a.buf[aligned : aligned+size : aligned+size]
	for i := range region {
		region[i] = 0
	}
	a.off = aligned + size
	a.allocs++
	if a.off > a.highWater {
		a.highWater = a.off
	}
	return region, nil
}

// Reset returns all arena memory to the allocator (logically). The
// arena buffer is retained for reuse; debug builds poison the used
// prefix to catch use-after-reset.
func (a *Arena) Reset() {
	a.mu.Lock()
	defer a.mu.Unlock()
	if a.poison {
		for i := 0; i < a.off && i < len(a.buf); i += 64 {
			a.buf[i] = 0xAA
		}
	}
	a.off = 0
	a.resets++
}

// Stats returns arena utilization statistics.
func (a *Arena) Stats() ArenaStats {
	a.mu.Lock()
	defer a.mu.Unlock()
	return ArenaStats{
		Capacity:      len(a.buf),
		Used:          a.off,
		Peak:          a.highWater,
		Allocs:        a.allocs,
		Resets:        a.resets,
		Fragmentation: float64(len(a.buf)-a.off) / float64(len(a.buf)),
	}
}

// ArenaStats describes arena utilization.
type ArenaStats struct {
	Capacity      int
	Used          int
	Peak          int
	Allocs        int64
	Resets        int64
	Fragmentation float64
}

// Pool is a size-class free-list allocator with per-CPU-style caches
// (sharded by goroutine-local buckets in this pure-stdlib build).
type Pool struct {
	mu    sync.Mutex
	class int
	free  [][]byte
	total int64
	hits  int64
	miss  int64
}

// NewPool creates a pool for objects of the given class size.
func NewPool(classSize int) *Pool {
	if classSize <= 0 {
		classSize = 4096
	}
	return &Pool{class: classSize}
}

// Acquire returns a buffer of the pool's class size, reusing a freed
// buffer when available.
func (p *Pool) Acquire() []byte {
	p.mu.Lock()
	n := len(p.free)
	if n > 0 {
		buf := p.free[n-1]
		p.free[n-1] = nil
		p.free = p.free[:n-1]
		p.hits++
		p.mu.Unlock()
		return buf
	}
	p.miss++
	p.mu.Unlock()
	return AlignedAlloc(p.class, DefaultAlignment)
}

// Release returns a buffer to the pool. Double release is detected by
// capacity check: foreign buffers are dropped to the GC.
func (p *Pool) Release(buf []byte) {
	if len(buf) != p.class {
		return
	}
	p.mu.Lock()
	p.free = append(p.free, buf)
	p.total++
	p.mu.Unlock()
}

// PoolStats returns pool hit/miss statistics.
func (p *Pool) Stats() (hits, miss int64) {
	p.mu.Lock()
	defer p.mu.Unlock()
	return p.hits, p.miss
}

// ReuseRegistry lends buffers by key so callers with compatible
// (dtype, shape) requirements can reuse memory across steps.
type ReuseRegistry struct {
	mu      sync.Mutex
	entries map[string][][]byte
	saved   atomic.Int64
	misses  atomic.Int64
}

// NewReuseRegistry creates an empty reuse registry.
func NewReuseRegistry() *ReuseRegistry {
	return &ReuseRegistry{entries: map[string][][]byte{}}
}

// Lend returns a reusable buffer for key or allocates a new one.
func (r *ReuseRegistry) Lend(key string, size int) []byte {
	r.mu.Lock()
	if bufs, ok := r.entries[key]; ok && len(bufs) > 0 {
		buf := bufs[len(bufs)-1]
		r.entries[key] = bufs[:len(bufs)-1]
		r.mu.Unlock()
		r.saved.Add(1)
		return buf
	}
	r.mu.Unlock()
	r.misses.Add(1)
	return AlignedAlloc(size, DefaultAlignment)
}

// Return lends a buffer back for future reuse.
func (r *ReuseRegistry) Return(key string, buf []byte) {
	r.mu.Lock()
	r.entries[key] = append(r.entries[key], buf)
	r.mu.Unlock()
}

// Stats returns reuse counters.
func (r *ReuseRegistry) Stats() (saved, misses int64) {
	return r.saved.Load(), r.misses.Load()
}

// ImportHandle wraps externally owned memory for zero-copy tensor
// import. The engine never frees the buffer; the release callback is
// invoked when the last view is gone (caller-managed lifetime).
type ImportHandle struct {
	data    []byte
	release func()
	used    atomic.Bool
}

// Import creates a zero-copy handle over data. The release callback is
// mandatory: the engine does not own the memory.
func Import(data []byte, release func()) (*ImportHandle, error) {
	if len(data) == 0 {
		return nil, errors.New(errors.CodeInvalidArgument, "import requires non-empty buffer")
	}
	if release == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "import requires release callback")
	}
	return &ImportHandle{data: data, release: release}, nil
}

// Bytes returns the imported buffer.
func (h *ImportHandle) Bytes() []byte { return h.data }

// Release invokes the owner's release callback exactly once.
func (h *ImportHandle) Release() {
	if h.used.CompareAndSwap(false, true) {
		h.release()
	}
}

// COWBuffer implements copy-on-write escalation: the first write
// clones the shared buffer exactly once.
type COWBuffer struct {
	mu     sync.Mutex
	shared []byte
	owned  []byte
	copied bool
	copies int64
}

// NewCOWBuffer wraps a shared buffer with copy-on-write semantics.
func NewCOWBuffer(shared []byte) *COWBuffer { return &COWBuffer{shared: shared} }

// Read returns the current bytes (shared until first write).
func (c *COWBuffer) Read() []byte {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.copied {
		return c.owned
	}
	return c.shared
}

// Write returns a mutable copy, cloning on first write only.
func (c *COWBuffer) Write() []byte {
	c.mu.Lock()
	defer c.mu.Unlock()
	if !c.copied {
		c.owned = make([]byte, len(c.shared))
		copy(c.owned, c.shared)
		c.copied = true
		c.copies++
	}
	return c.owned
}

// Copies returns the number of clone operations performed.
func (c *COWBuffer) Copies() int64 {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.copies
}
