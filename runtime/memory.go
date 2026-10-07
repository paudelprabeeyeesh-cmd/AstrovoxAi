package runtime

import (
	"sync"

	"github.com/astrovox/astrovox/internal/errors"
)

// MemoryStats reports allocator state.
type MemoryStats struct {
	AllocatedBytes int64
	PeakBytes      int64
	FreeBytes      int64
	LimitBytes     int64
	LiveBuffers    int64
	TotalAllocs    int64
	TotalFrees     int64
}

// MemoryManager tracks runtime buffer
// allocations against a configurable limit,
// backing allocations with pooled slices
// to cut GC pressure.
type MemoryManager struct {
	mu        sync.Mutex
	limit     int64
	allocated int64
	peak      int64
	live      int64
	allocs    int64
	frees     int64
	pool      sync.Pool
}

// NewMemoryManager creates a manager with
// the given byte limit. Limit <= 0 means
// unlimited.
func NewMemoryManager(limitBytes int64) *MemoryManager {
	return &MemoryManager{
		limit: limitBytes,
		pool: sync.Pool{
			New: func() any { return make([]float64, 0, 4096) },
		},
	}
}

// Allocate reserves n float64 elements.
func (m *MemoryManager) Allocate(n int) ([]float64, error) {
	if n < 0 {
		return nil, errors.New(errors.CodeInvalidArgument, "negative allocation").
			WithField("n", n)
	}
	bytes := int64(n) * 8
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.limit > 0 && m.allocated+bytes > m.limit {
		return nil, errors.New(errors.CodeOutOfMemory, "allocation exceeds limit").
			WithField("requested", bytes).
			WithField("allocated", m.allocated).
			WithField("limit", m.limit)
	}
	var buf []float64
	if pooled := m.pool.Get().([]float64); cap(pooled) >= n {
		buf = pooled[:n]
	} else {
		buf = make([]float64, n)
	}
	m.allocated += bytes
	m.live++
	m.allocs++
	if m.allocated > m.peak {
		m.peak = m.allocated
	}
	return buf, nil
}

// Free returns a buffer to the pool.
func (m *MemoryManager) Free(buf []float64) {
	if buf == nil {
		return
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	bytes := int64(cap(buf)) * 8
	if bytes > m.allocated {
		bytes = m.allocated
	}
	m.allocated -= bytes
	m.live--
	if m.live < 0 {
		m.live = 0
	}
	m.frees++
	if cap(buf) <= 1<<16 {
		m.pool.Put(buf[:0])
	}
}

// Stats returns the allocator state.
func (m *MemoryManager) Stats() MemoryStats {
	m.mu.Lock()
	defer m.mu.Unlock()
	free := int64(0)
	if m.limit > 0 {
		free = m.limit - m.allocated
	}
	return MemoryStats{
		AllocatedBytes: m.allocated,
		PeakBytes:      m.peak,
		FreeBytes:      free,
		LimitBytes:     m.limit,
		LiveBuffers:    m.live,
		TotalAllocs:    m.allocs,
		TotalFrees:     m.frees,
	}
}

// SetLimit changes the byte limit.
func (m *MemoryManager) SetLimit(limitBytes int64) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.limit = limitBytes
}

// Arena hands out bump allocations from a
// backing buffer, freeing everything at once.
type Arena struct {
	buf    []float64
	offset int
	mm     *MemoryManager
}

// NewArena creates an arena of n elements
// backed by the manager.
func NewArena(mm *MemoryManager, n int) (*Arena, error) {
	buf, err := mm.Allocate(n)
	if err != nil {
		return nil, err
	}
	return &Arena{buf: buf, mm: mm}, nil
}

// Allocate bumps the arena pointer.
func (a *Arena) Allocate(n int) ([]float64, error) {
	if n < 0 {
		return nil, errors.New(errors.CodeInvalidArgument, "negative allocation").
			WithField("n", n)
	}
	if a.offset+n > len(a.buf) {
		return nil, errors.New(errors.CodeOutOfMemory, "arena exhausted").
			WithField("free", len(a.buf)-a.offset).
			WithField("requested", n)
	}
	out := a.buf[a.offset : a.offset+n : a.offset+n]
	a.offset += n
	return out, nil
}

// Remaining returns the free element count.
func (a *Arena) Remaining() int { return len(a.buf) - a.offset }

// Reset rewinds the arena pointer without
// releasing the backing buffer.
func (a *Arena) Reset() { a.offset = 0 }

// Release returns the backing buffer to
// the manager.
func (a *Arena) Release() {
	if a.mm != nil && a.buf != nil {
		a.mm.Free(a.buf)
		a.buf = nil
	}
}
