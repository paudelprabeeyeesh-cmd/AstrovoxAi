// Package fixtures provides deterministic test fixtures:
// seeded random generators, tensor fixtures, temp-dir
// management, and golden-file comparison. All fixtures
// are hermetic: no network, no clock, and no filesystem
// access outside temp dirs.
package fixtures

import (
	"bytes"
	"flag"
	"fmt"
	"math/rand"
	"os"
	"path/filepath"
	"testing"

	"github.com/astrovox/astrovox/tensor"
)

// updateGolden is set by the -update flag to
// regenerate golden files instead of comparing.
var updateGolden = flag.Bool("update", false, "update golden files")

// DefaultSeed is the seed used by Seeded.
const DefaultSeed int64 = 42

// RNG returns a deterministic generator seeded by seed.
func RNG(seed int64) *rand.Rand {
	return rand.New(rand.NewSource(seed))
}

// Seeded returns the default deterministic generator.
func Seeded() *rand.Rand {
	return RNG(DefaultSeed)
}

// TensorSpec describes one deterministic tensor fixture.
type TensorSpec struct {
	DType tensor.DType
	Dims  []int
	Seed  int64
}

// Tensor builds a tensor from spec, filling it with
// deterministic pseudo-random values in [0, 1).
func Tensor(spec TensorSpec) (*tensor.Tensor, error) {
	src, err := tensor.New(spec.DType, spec.Dims)
	if err != nil {
		return nil, err
	}
	rng := RNG(spec.Seed)
	rank := len(spec.Dims)
	n := src.NumElements()
	idx := make([]int, rank)
	for i := 0; i < n; i++ {
		rem := i
		for d := rank - 1; d >= 0; d-- {
			idx[d] = rem % spec.Dims[d]
			rem /= spec.Dims[d]
		}
		if err := src.Set(spec.DType.Cast(rng.Float64()), idx...); err != nil {
			return nil, err
		}
	}
	return src, nil
}

// DTypeFixtures returns one tensor spec per supported
// dtype, all sharing dims and a per-dtype seed.
func DTypeFixtures(dims []int) []TensorSpec {
	specs := make([]TensorSpec, 0, int(tensor.NumDTypes))
	for d := tensor.DType(0); int(d) < int(tensor.NumDTypes); d++ {
		specs = append(specs, TensorSpec{DType: d, Dims: dims, Seed: int64(d) + 1})
	}
	return specs
}

// RandomDims returns deterministic random dimensions
// with rank in [1, maxRank] and sizes in [1, maxDim].
func RandomDims(rng *rand.Rand, maxRank, maxDim int) []int {
	rank := 1 + rng.Intn(maxRank)
	dims := make([]int, rank)
	for i := range dims {
		dims[i] = 1 + rng.Intn(maxDim)
	}
	return dims
}

// TempDir creates a unique temp directory removed on
// test cleanup.
func TempDir(t *testing.T) string {
	t.Helper()
	dir, err := os.MkdirTemp("", "astrovox-")
	if err != nil {
		t.Fatalf("TempDir: %v", err)
	}
	t.Cleanup(func() { _ = os.RemoveAll(dir) })
	return dir
}

// WriteFile writes data to a file named name inside a
// new temp dir and returns the file path.
func WriteFile(t *testing.T, name string, data []byte) string {
	t.Helper()
	path := filepath.Join(TempDir(t), name)
	if err := os.WriteFile(path, data, 0o644); err != nil {
		t.Fatalf("WriteFile(%s): %v", name, err)
	}
	return path
}

// Golden compares got against the golden file
// dir/testdata/name. When the -update flag is
// set, the golden file is (re)created instead.
func Golden(t *testing.T, dir, name string, got []byte) {
	t.Helper()
	if err := Compare(dir, name, got); err != nil {
		t.Errorf("Golden(%s): %v", name, err)
	}
}

// Compare returns nil when got equals the golden
// file dir/testdata/name, or a descriptive
// error. When the -update flag is set, the
// golden file is (re)created and nil is
// returned.
func Compare(dir, name string, got []byte) error {
	path := filepath.Join(dir, "testdata", name)
	if *updateGolden {
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			return fmt.Errorf("mkdir: %w", err)
		}
		if err := os.WriteFile(path, got, 0o644); err != nil {
			return fmt.Errorf("write: %w", err)
		}
		return nil
	}
	want, err := os.ReadFile(path)
	if err != nil {
		return fmt.Errorf("read: %w", err)
	}
	if !bytes.Equal(want, got) {
		return fmt.Errorf("mismatch:\n got: %q\nwant: %q", got, want)
	}
	return nil
}
