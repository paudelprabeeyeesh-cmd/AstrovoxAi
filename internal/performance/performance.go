package performance

import (
	"runtime"
	"sync"
	"sync/atomic"
)

// LazyValue delays computation until first access.
type LazyValue struct {
	compute func() interface{}
	value   interface{}
	loaded  uint32
}

// NewLazyValue creates a new lazy value.
func NewLazyValue(fn func() interface{}) *LazyValue {
	return &LazyValue{compute: fn}
}

// Get returns the value, computing it if needed.
func (l *LazyValue) Get() interface{} {
	if atomic.LoadUint32(&l.loaded) == 0 {
		l.value = l.compute()
		atomic.StoreUint32(&l.loaded, 1)
	}
	return l.value
}

// SIMDVector provides simple vector operations.
type SIMDVector struct {
	Data []float64
}

// NewSIMDVector creates a new vector.
func NewSIMDVector(size int) *SIMDVector {
	return &SIMDVector{Data: make([]float64, size)}
}

// Add performs element-wise addition.
func (v *SIMDVector) Add(other *SIMDVector) (*SIMDVector, error) {
	if len(v.Data) != len(other.Data) {
		return nil, &SizeMismatchError{}
	}
	out := NewSIMDVector(len(v.Data))
	for i := range v.Data {
		out.Data[i] = v.Data[i] + other.Data[i]
	}
	return out, nil
}

// SizeMismatchError indicates a vector size mismatch.
type SizeMismatchError struct{}

func (e *SizeMismatchError) Error() string {
	return "vector size mismatch"
}

// CacheLine represents a CPU cache line.
const CacheLineSize = 64

// AlignToCacheLine pads a size to the nearest cache line.
func AlignToCacheLine(size int) int {
	if size%CacheLineSize == 0 {
		return size
	}
	return ((size / CacheLineSize) + 1) * CacheLineSize
}

// NumCPU returns the number of logical CPUs.
func NumCPU() int {
	return runtime.NumCPU()
}

// ParallelFor runs a loop in parallel.
func ParallelFor(start, end int, fn func(int)) {
	if end <= start {
		return
	}
	workers := runtime.NumCPU()
	if workers > end-start {
		workers = end - start
	}
	chunk := (end - start) / workers
	if chunk == 0 {
		chunk = 1
	}

	var wg sync.WaitGroup
	for w := 0; w < workers; w++ {
		s := start + w*chunk
		e := s + chunk
		if w == workers-1 {
			e = end
		}
		if s >= e {
			continue
		}
		wg.Add(1)
		go func(s, e int) {
			defer wg.Done()
			for i := s; i < e; i++ {
				fn(i)
			}
		}(s, e)
	}
	wg.Wait()
}
