package fixtures

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"

	"github.com/astrovox/astrovox/tensor"
)

func TestRNG_Deterministic(t *testing.T) {
	a, b := RNG(7), RNG(7)
	for i := 0; i < 100; i++ {
		if x, y := a.Float64(), b.Float64(); x != y {
			t.Fatalf("RNG diverged at %d: %v != %v", i, x, y)
		}
	}
}

func TestRNG_DifferentSeeds(t *testing.T) {
	a, b := RNG(1), RNG(2)
	if a.Float64() == b.Float64() {
		t.Fatal("different seeds produced identical values")
	}
}

func TestSeeded_DefaultSeed(t *testing.T) {
	a, b := Seeded(), RNG(DefaultSeed)
	for i := 0; i < 100; i++ {
		if x, y := a.Float64(), b.Float64(); x != y {
			t.Fatalf("Seeded diverged from RNG(%d) at %d", DefaultSeed, i)
		}
	}
}

func TestTensor_Deterministic(t *testing.T) {
	spec := TensorSpec{DType: tensor.Float64, Dims: []int{3, 4}, Seed: 9}
	a, err := Tensor(spec)
	if err != nil {
		t.Fatal(err)
	}
	b, err := Tensor(spec)
	if err != nil {
		t.Fatal(err)
	}
	eq, err := a.Equal(b)
	if err != nil {
		t.Fatal(err)
	}
	if !eq {
		t.Fatal("same spec produced different tensors")
	}
}

func TestTensor_AllDtypes(t *testing.T) {
	for _, spec := range DTypeFixtures([]int{2, 2}) {
		src, err := Tensor(spec)
		if err != nil {
			t.Fatalf("dtype %s: %v", spec.DType, err)
		}
		if src.DType() != spec.DType {
			t.Fatalf("dtype = %s, want %s", src.DType(), spec.DType)
		}
		if src.NumElements() != 4 {
			t.Fatalf("elements = %d, want 4", src.NumElements())
		}
	}
}

func TestTensor_ValuesInRange(t *testing.T) {
	src, err := Tensor(TensorSpec{DType: tensor.Float64, Dims: []int{64}, Seed: 3})
	if err != nil {
		t.Fatal(err)
	}
	for _, v := range src.Float64() {
		if v < 0 || v >= 1 {
			t.Fatalf("value %v outside [0,1)", v)
		}
	}
}

func TestTensor_DifferentSeedsDiffer(t *testing.T) {
	a, err := Tensor(TensorSpec{DType: tensor.Float64, Dims: []int{16}, Seed: 1})
	if err != nil {
		t.Fatal(err)
	}
	b, err := Tensor(TensorSpec{DType: tensor.Float64, Dims: []int{16}, Seed: 2})
	if err != nil {
		t.Fatal(err)
	}
	eq, err := a.Equal(b)
	if err != nil {
		t.Fatal(err)
	}
	if eq {
		t.Fatal("different seeds produced identical tensors")
	}
}

func TestRandomDims_Bounds(t *testing.T) {
	rng := Seeded()
	for i := 0; i < 200; i++ {
		dims := RandomDims(rng, 5, 8)
		if len(dims) < 1 || len(dims) > 5 {
			t.Fatalf("rank %d outside [1,5]", len(dims))
		}
		for _, d := range dims {
			if d < 1 || d > 8 {
				t.Fatalf("dim %d outside [1,8]", d)
			}
		}
	}
}

func TestRandomDims_Deterministic(t *testing.T) {
	a, b := Seeded(), Seeded()
	for i := 0; i < 50; i++ {
		da, db := RandomDims(a, 4, 6), RandomDims(b, 4, 6)
		if len(da) != len(db) {
			t.Fatalf("rank diverged: %d != %d", len(da), len(db))
		}
		for j := range da {
			if da[j] != db[j] {
				t.Fatalf("dims diverged at %d: %v != %v", j, da, db)
			}
		}
	}
}

func TestTempDir_Exists(t *testing.T) {
	dir := TempDir(t)
	info, err := os.Stat(dir)
	if err != nil {
		t.Fatalf("TempDir not created: %v", err)
	}
	if !info.IsDir() {
		t.Fatal("TempDir path is not a directory")
	}
}

func TestWriteFile_Content(t *testing.T) {
	data := []byte("fixture-bytes")
	path := WriteFile(t, "data.bin", data)
	got, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, data) {
		t.Fatalf("content = %q, want %q", got, data)
	}
	if filepath.Base(path) != "data.bin" {
		t.Fatalf("base = %s, want data.bin", filepath.Base(path))
	}
}

func TestCompare_UpdateAndMatch(t *testing.T) {
	dir := TempDir(t)
	got := []byte("golden-content")
	old := *updateGolden
	*updateGolden = true
	err := Compare(dir, "g1.bin", got)
	*updateGolden = old
	if err != nil {
		t.Fatalf("Compare update: %v", err)
	}
	if err := Compare(dir, "g1.bin", got); err != nil {
		t.Fatalf("Compare match: %v", err)
	}
}

func TestCompare_Mismatch(t *testing.T) {
	dir := TempDir(t)
	old := *updateGolden
	*updateGolden = true
	_ = Compare(dir, "g2.bin", []byte("original"))
	*updateGolden = old
	err := Compare(dir, "g2.bin", []byte("changed"))
	if err == nil {
		t.Fatal("Compare mismatch returned nil")
	}
}

func TestCompare_Missing(t *testing.T) {
	dir := TempDir(t)
	if err := Compare(dir, "absent.bin", []byte("x")); err == nil {
		t.Fatal("Compare missing golden returned nil")
	}
}

func TestGolden_Reports(t *testing.T) {
	dir := TempDir(t)
	old := *updateGolden
	*updateGolden = true
	_ = Compare(dir, "g3.bin", []byte("v"))
	*updateGolden = old
	// Golden must not fail on a matching file.
	Golden(t, dir, "g3.bin", []byte("v"))
}

func TestDTypeFixtures_CoversAll(t *testing.T) {
	specs := DTypeFixtures([]int{2})
	if len(specs) != int(tensor.NumDTypes) {
		t.Fatalf("fixtures = %d, want %d", len(specs), int(tensor.NumDTypes))
	}
	seen := make(map[tensor.DType]bool)
	for _, spec := range specs {
		seen[spec.DType] = true
	}
	for d := tensor.DType(0); int(d) < int(tensor.NumDTypes); d++ {
		if !seen[d] {
			t.Fatalf("dtype %s missing from fixtures", d)
		}
	}
}

func TestTensor_ScalarFixture(t *testing.T) {
	src, err := Tensor(TensorSpec{DType: tensor.Float32, Dims: nil, Seed: 5})
	if err != nil {
		t.Fatal(err)
	}
	if !src.Shape().IsScalar() {
		t.Fatal("scalar fixture not scalar")
	}
	if src.NumElements() != 1 {
		t.Fatalf("elements = %d, want 1", src.NumElements())
	}
}

func TestRNG_IntSequence(t *testing.T) {
	rng := RNG(11)
	vals := make([]int, 10)
	for i := range vals {
		vals[i] = rng.Intn(100)
	}
	rng2 := RNG(11)
	for i, want := range vals {
		if got := rng2.Intn(100); got != want {
			t.Fatalf("int sequence diverged at %d: %d != %d", i, got, want)
		}
	}
}
