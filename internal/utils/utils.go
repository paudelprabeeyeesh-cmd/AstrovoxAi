// Package utils provides shared, allocation-light utilities used across the
// Astrovox engine: generic math helpers, deterministic RNG, hashing, and
// alignment primitives.
package utils

import (
	"crypto/rand"
	"encoding/binary"
	"hash/fnv"
	"math"
	"sync"
)

// Ordered is the constraint for generic ordered helpers.
type Ordered interface {
	~int | ~int8 | ~int16 | ~int32 | ~int64 |
		~uint | ~uint8 | ~uint16 | ~uint32 | ~uint64 | ~uintptr |
		~float32 | ~float64
}

// Min returns the smaller of two ordered values.
func Min[T Ordered](a, b T) T {
	if a < b {
		return a
	}
	return b
}

// Max returns the larger of two ordered values.
func Max[T Ordered](a, b T) T {
	if a > b {
		return a
	}
	return b
}

// Clamp returns v bounded to [lo, hi].
func Clamp[T Ordered](v, lo, hi T) T {
	if v < lo {
		return lo
	}
	if v > hi {
		return hi
	}
	return v
}

// Sum reduces an ordered slice.
func Sum[T Ordered](xs []T) T {
	var total T
	for _, x := range xs {
		total += x
	}
	return total
}

// IsPow2 reports whether n is a positive power of two.
func IsPow2(n int) bool { return n > 0 && n&(n-1) == 0 }

// AlignUp rounds n up to the next multiple of align (align must be a power of two).
func AlignUp(n, align int) int {
	if align <= 1 || n < 0 {
		return n
	}
	return (n + align - 1) &^ (align - 1)
}

// AlignDown rounds n down to the previous multiple of align.
func AlignDown(n, align int) int {
	if align <= 1 || n < 0 {
		return n
	}
	return n &^ (align - 1)
}

// DivCeil returns ceil(a/b) for positive b.
func DivCeil(a, b int) int {
	if b <= 0 {
		return 0
	}
	return (a + b - 1) / b
}

// Rand is a deterministic seeded RNG (splitmix64) safe for concurrent use.
type Rand struct {
	mu sync.Mutex
	s  uint64
}

// NewRand creates a deterministic RNG from a seed.
func NewRand(seed uint64) *Rand { return &Rand{s: seed | 1} }

// GlobalRand is the process-wide deterministic RNG, seeded from crypto/rand.
var GlobalRand = func() *Rand {
	var b [8]byte
	if _, err := rand.Read(b[:]); err != nil {
		return NewRand(0x9E3779B97F4A7C15)
	}
	return NewRand(binary.LittleEndian.Uint64(b[:]))
}()

// Uint64 returns the next pseudo-random uint64.
func (r *Rand) Uint64() uint64 {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.s += 0x9E3779B97F4A7C15
	z := r.s
	z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9
	z = (z ^ (z >> 27)) * 0x94D049BB133111EB
	return z ^ (z >> 31)
}

// Int63 returns a non-negative pseudo-random int63.
func (r *Rand) Int63() int64 { return int64(r.Uint64() & (1<<63 - 1)) }

// Intn returns a pseudo-random value in [0, n).
func (r *Rand) Intn(n int) int {
	if n <= 0 {
		return 0
	}
	return int(r.Uint64() % uint64(n))
}

// Float64 returns a pseudo-random float64 in [0, 1).
func (r *Rand) Float64() float64 {
	return float64(r.Int63()) / float64(1<<63)
}

// Float32 returns a pseudo-random float32 in [0, 1).
func (r *Rand) Float32() float32 { return float32(r.Float64()) }

// Shuffle permutes xs in place using Fisher-Yates.
func (r *Rand) Shuffle(xs []int) {
	for i := len(xs) - 1; i > 0; i-- {
		j := r.Intn(i + 1)
		xs[i], xs[j] = xs[j], xs[i]
	}
}

// Hash32 returns the FNV-1a 32-bit hash of data.
func Hash32(data []byte) uint32 {
	h := fnv.New32a()
	_, _ = h.Write(data)
	return h.Sum32()
}

// Hash64 returns the FNV-1a 64-bit hash of data.
func Hash64(data []byte) uint64 {
	h := fnv.New64a()
	_, _ = h.Write(data)
	return h.Sum64()
}

// HashString32 returns the FNV-1a 32-bit hash of a string.
func HashString32(s string) uint32 { return Hash32([]byte(s)) }

// HashString64 returns the FNV-1a 64-bit hash of a string.
func HashString64(s string) uint64 { return Hash64([]byte(s)) }

// NearEqual reports whether two float64 values are within rel tolerance
// (with an absolute floor for values near zero).
func NearEqual(a, b, relTol, absTol float64) bool {
	diff := math.Abs(a - b)
	if diff <= absTol {
		return true
	}
	scale := math.Max(math.Abs(a), math.Abs(b))
	if scale == 0 {
		return diff == 0
	}
	return diff/scale <= relTol
}

// ByteView returns an immutable view of b. The caller must not mutate b.
func ByteView(b []byte) []byte { return b[:len(b):len(b)] }
