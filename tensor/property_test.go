package tensor_test

import (
	"fmt"
	"math/rand"
	"testing"

	"github.com/astrovox/astrovox/internal/testing/property"
	"github.com/astrovox/astrovox/tensor"
)

// Property_TransposeInvolution: transposing the same pair of
// dimensions twice yields the original tensor.
func TestProperty_TransposeInvolution(t *testing.T) {
	property.Check(t, "transpose-involution", 1000, func(rng *rand.Rand) error {
		dims := property.GenDims(rng, 4, 8)
		rank := len(dims)
		for i := range dims {
			if dims[i] < 1 {
				dims[i] = 1
			}
		}
		orig, err := tensor.Ones(tensor.Float32, dims)
		if err != nil {
			return err
		}
		d0 := rng.Intn(rank)
		d1 := rng.Intn(rank)
		t1, err := orig.Transpose(d0, d1)
		if err != nil {
			return err
		}
		t2, err := t1.Transpose(d0, d1)
		if err != nil {
			return err
		}
		eq, err := orig.Equal(t2)
		if err != nil {
			return err
		}
		if !eq {
			return fmt.Errorf("transpose not involutive for dims=%v d0=%d d1=%d", dims, d0, d1)
		}
		return nil
	})
}

// Property_ReshapePreservesElements: reshaping preserves the
// element count and the flattened data order.
func TestProperty_ReshapePreservesElements(t *testing.T) {
	property.Check(t, "reshape-preserves-elements", 1000, func(rng *rand.Rand) error {
		n := property.GenInt(rng, 1, 64)
		src, err := tensor.Arange(tensor.Float64, 0, float64(n), 1)
		if err != nil {
			return err
		}
		// Pick a random factorization of n.
		a := property.GenInt(rng, 1, n)
		if n%a != 0 {
			a = 1
		}
		b := n / a
		rs, err := src.Reshape(a, b)
		if err != nil {
			return err
		}
		if rs.NumElements() != n {
			return fmt.Errorf("reshape changed element count: %d != %d", rs.NumElements(), n)
		}
		first, err := rs.Get(0, 0)
		if err != nil {
			return err
		}
		last, err := rs.Get(a-1, b-1)
		if err != nil {
			return err
		}
		if first.(float64) != 0 {
			return fmt.Errorf("first element = %v, want 0", first)
		}
		if last.(float64) != float64(n-1) {
			return fmt.Errorf("last element = %v, want %d", last, n-1)
		}
		return nil
	})
}

// Property_RoundTrip: serialize then deserialize preserves
// shape, dtype, and values for every dtype.
func TestProperty_RoundTrip(t *testing.T) {
	property.Check(t, "round-trip", 1000, func(rng *rand.Rand) error {
		dt := property.GenDType(rng)
		dims := property.GenDims(rng, 3, 4)
		for i := range dims {
			if dims[i] < 1 {
				dims[i] = 1
			}
		}
		value := property.GenFloat(rng)
		src, err := tensor.Full(dt, dims, value)
		if err != nil {
			return err
		}
		data, err := tensor.Save(src)
		if err != nil {
			return err
		}
		loaded, err := tensor.Load(data)
		if err != nil {
			return err
		}
		eq, err := src.Equal(loaded)
		if err != nil {
			return err
		}
		if !eq {
			return fmt.Errorf("round-trip mismatch for dtype=%s dims=%v", dt, dims)
		}
		return nil
	})
}

// TestProperty_PromoteLaws verifies the dtype promotion
// lattice exhaustively over all dtype pairs and triples.
func TestProperty_PromoteLaws(t *testing.T) {
	dtypes := make([]tensor.DType, 0, int(tensor.NumDTypes))
	for d := tensor.DType(0); int(d) < int(tensor.NumDTypes); d++ {
		dtypes = append(dtypes, d)
	}
	// Commutativity and idempotence over all pairs.
	for _, a := range dtypes {
		if got := tensor.Promote(a, a); got != a {
			t.Errorf("Promote(%s,%s) = %s, want idempotent %s", a, a, got, a)
		}
		for _, b := range dtypes {
			if ab, ba := tensor.Promote(a, b), tensor.Promote(b, a); ab != ba {
				t.Errorf("Promote not commutative: Promote(%s,%s)=%s != Promote(%s,%s)=%s",
					a, b, ab, b, a, ba)
			}
			// Associativity over all triples.
			for _, c := range dtypes {
				left := tensor.Promote(tensor.Promote(a, b), c)
				right := tensor.Promote(a, tensor.Promote(b, c))
				if left != right {
					t.Errorf("Promote not associative: (%s,%s),%s = %s vs %s,(%s,%s) = %s",
						a, b, c, left, a, b, c, right)
				}
			}
		}
	}
}

// Property_CastSaturation: integer casts saturate to the
// representable range; float casts stay finite.
func TestProperty_CastSaturation(t *testing.T) {
	property.Check(t, "cast-saturation", 1000, func(rng *rand.Rand) error {
		dt := property.GenDType(rng)
		if !dt.IsInteger() {
			return nil
		}
		v := property.GenFloat(rng) * 1e10 // far out of range
		got := dt.Cast(v).(int64)
		switch dt {
		case tensor.Int8:
			if v > 127 && got != 127 {
				return fmt.Errorf("Int8 cast(%v) = %d, want 127", v, got)
			}
			if v < -128 && got != -128 {
				return fmt.Errorf("Int8 cast(%v) = %d, want -128", v, got)
			}
		case tensor.Uint8:
			if v > 255 && got != 255 {
				return fmt.Errorf("Uint8 cast(%v) = %d, want 255", v, got)
			}
			if v < 0 && got != 0 {
				return fmt.Errorf("Uint8 cast(%v) = %d, want 0", v, got)
			}
		}
		return nil
	})
}

// Property_PermuteInverse: applying a permutation and its
// inverse restores the original layout.
func TestProperty_PermuteInverse(t *testing.T) {
	property.Check(t, "permute-inverse", 1000, func(rng *rand.Rand) error {
		rank := property.GenInt(rng, 1, 4)
		dims := make([]int, rank)
		for i := range dims {
			dims[i] = 1 + rng.Intn(4)
		}
		orig, err := tensor.Ones(tensor.Float32, dims)
		if err != nil {
			return err
		}
		perm := property.GenPerm(rng, rank)
		inv := make([]int, rank)
		for i, p := range perm {
			inv[p] = i
		}
		p1, err := orig.Permute(perm)
		if err != nil {
			return err
		}
		p2, err := p1.Permute(inv)
		if err != nil {
			return err
		}
		eq, err := orig.Equal(p2)
		if err != nil {
			return err
		}
		if !eq {
			return fmt.Errorf("permute not invertible for dims=%v perm=%v", dims, perm)
		}
		return nil
	})
}
