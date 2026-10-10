// Package runtime provides NUMA-aware memory allocation.
package runtime

import (
	"errors"
	"runtime"
	"sync"
	"sync/atomic"
	"unsafe"
)

// NUMAAllocator provides NUMA-aware memory allocation.
// It maintains per-NUMA-node memory pools to minimize cross-node traffic.
type NUMAAllocator struct {
	nodes     int
	pools     []*NumaPool
	hugePages bool
	pageSize  int
	stats     AllocatorStats
	allocFunc func(size int) (unsafe.Pointer, error)
	freeFunc  func(ptr unsafe.Pointer, size int) error
	mu        sync.Mutex
}

// NumaPool is a memory pool for a specific NUMA node.
type NumaPool struct {
	nodeID      int
	blocks      []*MemoryBlock
	freeLists   map[int]*FreeList // size class -> free list
	largeBlocks []*MemoryBlock    // For allocations > 1MB
	stats       PoolStats
	mu          sync.Mutex
}

// MemoryBlock represents a block of memory.
type MemoryBlock struct {
	ptr    unsafe.Pointer
	size   int
	nodeID int
	inUse  atomic.Bool
	next   *MemoryBlock
	prev   *MemoryBlock
}

// FreeList is a lock-free free list for a size class.
type FreeList struct {
	head atomic.Pointer[MemoryBlock]
	size int
}

// AllocatorStats holds allocator statistics.
type AllocatorStats struct {
	TotalAllocated   uint64
	TotalFreed       uint64
	CurrentAllocated uint64
	NumAllocations   uint64
	NumFrees         uint64
	CrossNodeAllocs  uint64
}

// PoolStats holds per-pool statistics.
type PoolStats struct {
	Allocated uint64
	Freed     uint64
	InUse     uint64
	Blocks    int
}

// AllocConfig configures the NUMA allocator.
type AllocConfig struct {
	Nodes       int
	HugePages   bool
	PageSize    int
	InitialSize int // Initial pool size per node
	AllocFunc   func(size int) (unsafe.Pointer, error)
	FreeFunc    func(ptr unsafe.Pointer, size int) error
}

// DefaultAllocConfig returns a default configuration.
func DefaultAllocConfig() *AllocConfig {
	return &AllocConfig{
		Nodes:       runtime.NumCPU(), // Approximation
		HugePages:   false,
		PageSize:    4096,
		InitialSize: 64 * 1024 * 1024, // 64MB per node
	}
}

// NewNUMAAllocator creates a new NUMA-aware allocator.
func NewNUMAAllocator(config *AllocConfig) *NUMAAllocator {
	if config == nil {
		config = DefaultAllocConfig()
	}

	// Detect actual NUMA nodes if possible
	nodes := config.Nodes
	if nodes <= 0 {
		nodes = runtime.NumCPU()
	}

	na := &NUMAAllocator{
		nodes:     nodes,
		pools:     make([]*NumaPool, nodes),
		hugePages: config.HugePages,
		pageSize:  config.PageSize,
		allocFunc: config.AllocFunc,
		freeFunc:  config.FreeFunc,
	}

	// Use default alloc/free if not provided
	if na.allocFunc == nil {
		na.allocFunc = defaultAlloc
	}
	if na.freeFunc == nil {
		na.freeFunc = defaultFree
	}

	// Initialize pools
	for i := 0; i < nodes; i++ {
		na.pools[i] = newNumaPool(i, config.InitialSize)
	}

	return na
}

func newNumaPool(nodeID, initialSize int) *NumaPool {
	pool := &NumaPool{
		nodeID:    nodeID,
		freeLists: make(map[int]*FreeList),
	}

	// Initialize size classes: 64B, 128B, 256B, 512B, 1KB, 2KB, 4KB, 8KB, 16KB, 32KB, 64KB, 128KB, 256KB, 512KB, 1MB
	for sz := 64; sz <= 1024*1024; sz *= 2 {
		pool.freeLists[sz] = &FreeList{size: sz}
	}

	return pool
}

// defaultAlloc uses runtime allocator (platform-specific in real impl).
func defaultAlloc(size int) (unsafe.Pointer, error) {
	// In production, use mmap/VirtualAlloc with NUMA hints
	// For now, use Go's allocator
	buf := make([]byte, size)
	return unsafe.Pointer(&buf[0]), nil
}

func defaultFree(ptr unsafe.Pointer, size int) error {
	// In production, use munmap/VirtualFree
	return nil
}

// Alloc allocates memory on the preferred NUMA node.
// If nodeID < 0, uses current thread's preferred node.
func (na *NUMAAllocator) Alloc(size int, nodeID int) (unsafe.Pointer, error) {
	if size <= 0 {
		return nil, errors.New("invalid size")
	}

	// Determine target node
	if nodeID < 0 || nodeID >= na.nodes {
		nodeID = na.getCurrentNode()
	}

	// Round up to size class
	sizeClass := roundUpSizeClass(size)

	pool := na.pools[nodeID]
	ptr := pool.alloc(sizeClass)

	if ptr == nil {
		// Try other nodes (cross-node allocation)
		atomic.AddUint64(&na.stats.CrossNodeAllocs, 1)
		for i := 0; i < na.nodes; i++ {
			if i == nodeID {
				continue
			}
			ptr = na.pools[i].alloc(sizeClass)
			if ptr != nil {
				break
			}
		}
	}

	if ptr == nil {
		// Allocate new block from OS
		ptr, _ = na.allocFunc(sizeClass)
		if ptr != nil {
			block := &MemoryBlock{ptr: ptr, size: sizeClass, nodeID: nodeID}
			block.inUse.Store(true)
			atomic.AddUint64(&na.stats.TotalAllocated, uint64(sizeClass))
			atomic.AddUint64(&na.stats.CurrentAllocated, uint64(sizeClass))
			atomic.AddUint64(&na.stats.NumAllocations, 1)
			return ptr, nil
		}
		return nil, errors.New("out of memory")
	}

	atomic.AddUint64(&na.stats.TotalAllocated, uint64(sizeClass))
	atomic.AddUint64(&na.stats.CurrentAllocated, uint64(sizeClass))
	atomic.AddUint64(&na.stats.NumAllocations, 1)
	return ptr, nil
}

// Free returns memory to the appropriate pool.
func (na *NUMAAllocator) Free(ptr unsafe.Pointer, size int) error {
	if ptr == nil || size <= 0 {
		return errors.New("invalid arguments")
	}

	sizeClass := roundUpSizeClass(size)

	// Try to find the block's node (simplified: use current node)
	nodeID := na.getCurrentNode()
	pool := na.pools[nodeID]
	pool.free(ptr, sizeClass)

	atomic.AddUint64(&na.stats.TotalFreed, uint64(sizeClass))
	atomic.AddUint64(&na.stats.CurrentAllocated, ^uint64(sizeClass-1)) // Subtract
	atomic.AddUint64(&na.stats.NumFrees, 1)
	return nil
}

func (p *NumaPool) alloc(sizeClass int) unsafe.Pointer {
	fl := p.freeLists[sizeClass]
	if fl == nil {
		return nil
	}

	for {
		head := fl.head.Load()
		if head == nil {
			return nil
		}
		if fl.head.CompareAndSwap(head, head.next) {
			head.inUse.Store(true)
			return head.ptr
		}
	}
}

func (p *NumaPool) free(ptr unsafe.Pointer, sizeClass int) {
	fl := p.freeLists[sizeClass]
	if fl == nil {
		return
	}

	block := &MemoryBlock{ptr: ptr, size: sizeClass, nodeID: p.nodeID}
	block.inUse.Store(false)

	for {
		head := fl.head.Load()
		block.next = head
		if fl.head.CompareAndSwap(head, block) {
			return
		}
	}
}

func (p *NumaPool) Stats() PoolStats {
	return PoolStats{
		Allocated: atomic.LoadUint64(&p.stats.Allocated),
		Freed:     atomic.LoadUint64(&p.stats.Freed),
		InUse:     atomic.LoadUint64(&p.stats.InUse),
		Blocks:    len(p.blocks),
	}
}

// roundUpSizeClass rounds up to the nearest power of 2.
func roundUpSizeClass(size int) int {
	if size <= 64 {
		return 64
	}
	size--
	size |= size >> 1
	size |= size >> 2
	size |= size >> 4
	size |= size >> 8
	size |= size >> 16
	size++
	if size > 1024*1024 {
		size = ((size + 1024*1024 - 1) / (1024 * 1024)) * (1024 * 1024)
	}
	return size
}

// getCurrentNode returns the current thread's NUMA node.
// Simplified: uses thread ID modulo nodes.
func (na *NUMAAllocator) getCurrentNode() int {
	// In production, use numa_get_cpu() / GetCurrentProcessorNumber()
	return int(uint64(runtime.GOMAXPROCS(0)) % uint64(na.nodes))
}

// Stats returns allocator statistics.
func (na *NUMAAllocator) Stats() AllocatorStats {
	return AllocatorStats{
		TotalAllocated:   atomic.LoadUint64(&na.stats.TotalAllocated),
		TotalFreed:       atomic.LoadUint64(&na.stats.TotalFreed),
		CurrentAllocated: atomic.LoadUint64(&na.stats.CurrentAllocated),
		NumAllocations:   atomic.LoadUint64(&na.stats.NumAllocations),
		NumFrees:         atomic.LoadUint64(&na.stats.NumFrees),
		CrossNodeAllocs:  atomic.LoadUint64(&na.stats.CrossNodeAllocs),
	}
}

// PoolStats returns per-node pool statistics.
func (na *NUMAAllocator) PoolStats() []PoolStats {
	stats := make([]PoolStats, na.nodes)
	for i, p := range na.pools {
		stats[i] = p.Stats()
	}
	return stats
}

// TensorPool provides tensor-aware memory pooling.
type TensorPool struct {
	allocator *NUMAAllocator
	pools     map[string]*tensorPoolEntry // key: "shape:dtype"
	mu        sync.Mutex
	stats     TensorPoolStats
}

type tensorPoolEntry struct {
	shape     []int
	dtype     string
	freeList  chan *TensorWrapper
	sizeClass int
}

type TensorWrapper struct {
	ptr   unsafe.Pointer
	data  []byte
	shape []int
	dtype string
	inUse atomic.Bool
	pool  *tensorPoolEntry
}

type TensorPoolStats struct {
	Hits        uint64
	Misses      uint64
	Allocations uint64
	Frees       uint64
}

func NewTensorPool(allocator *NUMAAllocator) *TensorPool {
	return &TensorPool{
		allocator: allocator,
		pools:     make(map[string]*tensorPoolEntry),
	}
}

func (tp *TensorPool) Get(shape []int, dtype string) (*TensorWrapper, error) {
	key := shapeKey(shape, dtype)
	tp.mu.Lock()
	entry, ok := tp.pools[key]
	if !ok {
		entry = &tensorPoolEntry{
			shape:     shape,
			dtype:     dtype,
			freeList:  make(chan *TensorWrapper, 32),
			sizeClass: roundUpSizeClass(tensorSize(shape, dtype)),
		}
		tp.pools[key] = entry
	}
	tp.mu.Unlock()

	select {
	case tw := <-entry.freeList:
		atomic.AddUint64(&tp.stats.Hits, 1)
		tw.inUse.Store(true)
		return tw, nil
	default:
		atomic.AddUint64(&tp.stats.Misses, 1)
		atomic.AddUint64(&tp.stats.Allocations, 1)
		size := entry.sizeClass
		ptr, err := tp.allocator.Alloc(size, -1)
		if err != nil {
			return nil, err
		}
		tw := &TensorWrapper{
			ptr:   ptr,
			data:  unsafe.Slice((*byte)(ptr), size),
			shape: shape,
			dtype: dtype,
			pool:  entry,
		}
		tw.inUse.Store(true)
		return tw, nil
	}
}

func (tp *TensorPool) Put(tw *TensorWrapper) {
	if tw == nil || !tw.inUse.Load() {
		return
	}
	tw.inUse.Store(false)
	select {
	case tw.pool.freeList <- tw:
		atomic.AddUint64(&tp.stats.Frees, 1)
	default:
		// Pool full, return to allocator
		tp.allocator.Free(tw.ptr, len(tw.data))
		atomic.AddUint64(&tp.stats.Frees, 1)
	}
}

func (tp *TensorPool) Stats() TensorPoolStats {
	return TensorPoolStats{
		Hits:        atomic.LoadUint64(&tp.stats.Hits),
		Misses:      atomic.LoadUint64(&tp.stats.Misses),
		Allocations: atomic.LoadUint64(&tp.stats.Allocations),
		Frees:       atomic.LoadUint64(&tp.stats.Frees),
	}
}

func shapeKey(shape []int, dtype string) string {
	s := dtype + ":"
	for _, d := range shape {
		s += itoa(d) + ","
	}
	return s
}

func tensorSize(shape []int, dtype string) int {
	size := 1
	for _, d := range shape {
		size *= d
	}
	switch dtype {
	case "float64", "int64", "uint64":
		return size * 8
	case "float32", "int32", "uint32":
		return size * 4
	case "int16", "uint16":
		return size * 2
	case "int8", "uint8", "bool":
		return size
	default:
		return size * 8
	}
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
		n = -n
	}
	var buf [20]byte
	pos := len(buf)
	for n > 0 {
		pos--
		buf[pos] = byte('0' + n%10)
		n /= 10
	}
	if neg {
		pos--
		buf[pos] = '-'
	}
	return string(buf[pos:])
}

// ArenaAllocator provides arena-based allocation for batch operations.
type ArenaAllocator struct {
	allocator *NUMAAllocator
	arenas    []*Arena
	current   int
	mu        sync.Mutex
}

type Arena struct {
	ptr       unsafe.Pointer
	size      int
	offset    int
	nodeID    int
	allocator *NUMAAllocator
}

func NewArenaAllocator(allocator *NUMAAllocator, arenaSize int, numArenas int) *ArenaAllocator {
	if arenaSize <= 0 {
		arenaSize = 64 * 1024 * 1024 // 64MB
	}
	if numArenas <= 0 {
		numArenas = runtime.NumCPU()
	}

	aa := &ArenaAllocator{
		allocator: allocator,
		arenas:    make([]*Arena, numArenas),
	}

	for i := 0; i < numArenas; i++ {
		ptr, _ := allocator.Alloc(arenaSize, i%allocator.nodes)
		aa.arenas[i] = &Arena{
			ptr:       ptr,
			size:      arenaSize,
			offset:    0,
			nodeID:    i % allocator.nodes,
			allocator: allocator,
		}
	}

	return aa
}

func (aa *ArenaAllocator) Alloc(size int) (unsafe.Pointer, error) {
	aa.mu.Lock()
	defer aa.mu.Unlock()

	// Try current arena
	for i := 0; i < len(aa.arenas); i++ {
		idx := (aa.current + i) % len(aa.arenas)
		arena := aa.arenas[idx]
		if arena.offset+size <= arena.size {
			ptr := unsafe.Pointer(uintptr(arena.ptr) + uintptr(arena.offset))
			arena.offset += size
			aa.current = idx
			return ptr, nil
		}
	}

	// Allocate new arena
	ptr, err := aa.allocator.Alloc(size, -1)
	if err != nil {
		return nil, err
	}
	return ptr, nil
}

func (aa *ArenaAllocator) Reset() {
	aa.mu.Lock()
	defer aa.mu.Unlock()
	for _, arena := range aa.arenas {
		arena.offset = 0
	}
	aa.current = 0
}
