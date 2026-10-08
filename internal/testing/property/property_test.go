package property

import (
	"errors"
	"math/rand"
	"reflect"
	"testing"

	"github.com/astrovox/astrovox/tensor"
)

func TestCheck(t *testing.T) {
	Check(t, "always-true", 100, func(rng *rand.Rand) error {
		if rng.Int() < 0 {
			return errors.New("impossible")
		}
		return nil
	})
}

func TestCheckReportsFailure(t *testing.T) {
	call := 0
	failures := Run("fails-on-first", 10, func(rng *rand.Rand) error {
		call++
		if call == 1 {
			return errors.New("first case fails")
		}
		return nil
	})
	if len(failures) != 1 {
		t.Fatalf("failures = %d, want 1", len(failures))
	}
	if failures[0].Index != 0 {
		t.Fatalf("first failure at case %d, want 0", failures[0].Index)
	}
}

func TestRunDeterministic(t *testing.T) {
	gen := func() []CaseFailure {
		return Run("gen", 10, func(rng *rand.Rand) error {
			if rng.Intn(2) == 0 {
				return errors.New("half fail")
			}
			return nil
		})
	}
	first := gen()
	second := gen()
	if len(first) != len(second) {
		t.Fatalf("non-deterministic: %d vs %d failures", len(first), len(second))
	}
	for i := range first {
		if first[i].Index != second[i].Index {
			t.Fatalf("failure index %d != %d", first[i].Index, second[i].Index)
		}
	}
}

func TestGenDims(t *testing.T) {
	rng := rand.New(rand.NewSource(1))
	for i := 0; i < 100; i++ {
		dims := GenDims(rng, 4, 8)
		if len(dims) < 1 || len(dims) > 4 {
			t.Fatalf("rank out of range: %d", len(dims))
		}
		for _, d := range dims {
			if d < 0 || d > 8 {
				t.Fatalf("dim out of range: %d", d)
			}
		}
	}
}

func TestGenDType(t *testing.T) {
	rng := rand.New(rand.NewSource(1))
	for i := 0; i < 100; i++ {
		dt := GenDType(rng)
		if int(dt) < 0 || int(dt) >= int(tensor.NumDTypes) {
			t.Fatalf("dtype out of range: %d", int(dt))
		}
	}
}

func TestGenInt(t *testing.T) {
	rng := rand.New(rand.NewSource(1))
	for i := 0; i < 100; i++ {
		v := GenInt(rng, -5, 5)
		if v < -5 || v > 5 {
			t.Fatalf("int out of range: %d", v)
		}
	}
}

func TestGenFloat(t *testing.T) {
	rng := rand.New(rand.NewSource(1))
	for i := 0; i < 100; i++ {
		v := GenFloat(rng)
		if v < -1e3 || v > 1e3 {
			t.Fatalf("float out of range: %v", v)
		}
	}
}

func TestGenPerm(t *testing.T) {
	rng := rand.New(rand.NewSource(1))
	for i := 0; i < 100; i++ {
		p := GenPerm(rng, 5)
		seen := make(map[int]bool)
		for _, v := range p {
			if v < 0 || v >= 5 || seen[v] {
				t.Fatalf("invalid permutation: %v", p)
			}
			seen[v] = true
		}
	}
}

func TestCheckDeterministic(t *testing.T) {
	run := func() int {
		count := 0
		Check(t, "count", 10, func(rng *rand.Rand) error {
			count++
			return nil
		})
		return count
	}
	Equal(t, run(), 10)
	Equal(t, run(), 10)
}

func Equal[T any](t *testing.T, got, want T) {
	t.Helper()
	if !reflect.DeepEqual(got, want) {
		t.Errorf("got %v, want %v", got, want)
	}
}
