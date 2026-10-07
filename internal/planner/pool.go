package planner

import "github.com/astrovox/astrovox/internal/memory"

// PoolManager wraps the memory pool for planner use.
type PoolManager struct {
	pool *memory.Pool
}

// NewPoolManager creates a new pool manager with a fixed block size.
func NewPoolManager(blockSize int) *PoolManager {
	return &PoolManager{
		pool: memory.NewPool(blockSize),
	}
}

// Acquire gets a block from the pool.
func (m *PoolManager) Acquire(size int) []byte {
	_ = size
	return m.pool.Acquire()
}

// Release returns a block to the pool.
func (m *PoolManager) Release(buf []byte) {
	m.pool.Release(buf)
}

// Stats returns pool statistics.
func (m *PoolManager) Stats() (cached, blockSize int) {
	return m.pool.Stats()
}
