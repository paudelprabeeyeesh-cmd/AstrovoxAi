package memory

import (
	"errors"
	"sync"
)

// Pool manages a pool of reusable memory blocks.
type Pool struct {
	blocks [][]byte
	mu     sync.Mutex
	size   int
}

// NewPool creates a new memory pool with fixed-size blocks.
func NewPool(size int) *Pool {
	return &Pool{size: size}
}

// Acquire gets a block from the pool or allocates a new one.
func (p *Pool) Acquire() []byte {
	p.mu.Lock()
	defer p.mu.Unlock()
	if len(p.blocks) > 0 {
		b := p.blocks[len(p.blocks)-1]
		p.blocks = p.blocks[:len(p.blocks)-1]
		return b
	}
	return make([]byte, p.size)
}

// Release returns a block to the pool.
func (p *Pool) Release(b []byte) {
	if b == nil {
		return
	}
	p.mu.Lock()
	defer p.mu.Unlock()
	p.blocks = append(p.blocks, b)
}

// Reset clears all cached blocks.
func (p *Pool) Reset() {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.blocks = nil
}

// Stats returns pool statistics.
func (p *Pool) Stats() (cached, size int) {
	p.mu.Lock()
	defer p.mu.Unlock()
	return len(p.blocks), p.size
}

// Arena is a bump allocator for temporary allocations.
type Arena struct {
	buf   []byte
	off   int
	mu    sync.Mutex
	pools map[int]*Pool
}

// NewArena creates a new arena allocator.
func NewArena(initialSize int) *Arena {
	return &Arena{
		buf:   make([]byte, initialSize),
		pools: make(map[int]*Pool),
	}
}

// Alloc allocates a temporary buffer of the given size.
func (a *Arena) Alloc(size int) ([]byte, error) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if a.off+size > len(a.buf) {
		return nil, errors.New("arena exhausted")
	}
	b := a.buf[a.off : a.off+size]
	a.off += size
	return b, nil
}

// Reset resets the arena to the beginning.
func (a *Arena) Reset() {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.off = 0
}

// GetPool returns a pool for a specific block size.
func (a *Arena) GetPool(size int) *Pool {
	if p, ok := a.pools[size]; ok {
		return p
	}
	p := NewPool(size)
	a.pools[size] = p
	return p
}

// BufferReuser reuses slices of a specific shape and dtype.
type BufferReuser struct {
	pools map[string]*Pool
	mu    sync.Mutex
}

// NewBufferReuser creates a new buffer reuser.
func NewBufferReuser() *BufferReuser {
	return &BufferReuser{pools: make(map[string]*Pool)}
}

// Key generates a pool key from shape and dtype.
func Key(shape []int, dtype string) string {
	// Simple key; can be improved with hashing.
	key := dtype + "|"
	for _, dim := range shape {
		key += string(rune(dim)) + ","
	}
	return key
}

// Acquire gets a buffer for the given shape and dtype.
func (b *BufferReuser) Acquire(shape []int, dtype string) []byte {
	size := 1
	for _, dim := range shape {
		size *= dim
	}
	key := Key(shape, dtype)
	b.mu.Lock()
	p := b.pools[key]
	if p == nil {
		p = NewPool(size)
		b.pools[key] = p
	}
	b.mu.Unlock()
	return p.Acquire()
}

// Release returns a buffer to the reuser.
func (b *BufferReuser) Release(shape []int, dtype string, buf []byte) {
	key := Key(shape, dtype)
	b.mu.Lock()
	p := b.pools[key]
	if p == nil {
		p = NewPool(len(buf))
		b.pools[key] = p
	}
	b.mu.Unlock()
	p.Release(buf)
}

// LeakDetector tracks allocations to detect leaks.
type LeakDetector struct {
	allocations map[string]int
	mu          sync.Mutex
}

// NewLeakDetector creates a new leak detector.
func NewLeakDetector() *LeakDetector {
	return &LeakDetector{allocations: make(map[string]int)}
}

// Record records an allocation.
func (l *LeakDetector) Record(label string) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.allocations[label]++
}

// Release records a deallocation.
func (l *LeakDetector) Release(label string) {
	l.mu.Lock()
	defer l.mu.Unlock()
	if count, ok := l.allocations[label]; ok && count > 0 {
		l.allocations[label] = count - 1
	}
}

// Report returns a map of leaked labels.
func (l *LeakDetector) Report() map[string]int {
	l.mu.Lock()
	defer l.mu.Unlock()
	leaks := make(map[string]int)
	for label, count := range l.allocations {
		if count > 0 {
			leaks[label] = count
		}
	}
	return leaks
}
