// Package property provides a deterministic property-based
// testing framework: seeded generators and invariant checking
// in the style of fast-check, using only the standard library.
package property

import (
	"math"
	"math/rand"
	"testing"

	"github.com/astrovox/astrovox/tensor"
)

// CaseFailure records one failing property case.
type CaseFailure struct {
	Name  string
	Index int
	Err   error
}

// Run executes fn over cases independent random cases,
// each seeded by its index so any failure is
// reproducible by re-running the single index.
// Run is pure: it never touches testing.T.
func Run(name string, cases int, fn func(rng *rand.Rand) error) []CaseFailure {
	var failures []CaseFailure
	for i := 0; i < cases; i++ {
		rng := rand.New(rand.NewSource(int64(i)))
		if err := fn(rng); err != nil {
			failures = append(failures, CaseFailure{
				Name: name, Index: i, Err: err,
			})
		}
	}
	return failures
}

// Check runs a property over cases independent random
// cases and reports each failure on t.
func Check(t *testing.T, name string, cases int, fn func(rng *rand.Rand) error) {
	t.Helper()
	for _, f := range Run(name, cases, fn) {
		t.Errorf("%s: case %d: %v", f.Name, f.Index, f.Err)
	}
}

// GenDims returns a random shape with rank in [1, maxRank]
// and dimension sizes in [0, maxDim].
func GenDims(rng *rand.Rand, maxRank, maxDim int) []int {
	rank := 1 + rng.Intn(maxRank)
	dims := make([]int, rank)
	for i := range dims {
		dims[i] = rng.Intn(maxDim + 1)
	}
	return dims
}

// GenDType returns a random valid DType.
func GenDType(rng *rand.Rand) tensor.DType {
	return tensor.DType(rng.Intn(int(tensor.NumDTypes)))
}

// GenInt returns a random integer in [lo, hi].
func GenInt(rng *rand.Rand, lo, hi int) int {
	if hi < lo {
		hi = lo
	}
	return lo + rng.Intn(hi-lo+1)
}

// GenFloat returns a random finite float in [-1e3, 1e3].
func GenFloat(rng *rand.Rand) float64 {
	for {
		v := (rng.Float64() - 0.5) * 2e3
		if !math.IsNaN(v) && !math.IsInf(v, 0) {
			return v
		}
	}
}

// GenPerm returns a random permutation of [0, n).
func GenPerm(rng *rand.Rand, n int) []int {
	p := make([]int, n)
	for i := range p {
		p[i] = i
	}
	rng.Shuffle(n, func(i, j int) { p[i], p[j] = p[j], p[i] })
	return p
}
