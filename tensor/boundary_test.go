package tensor_test

import (
	"fmt"
	"math"
	"testing"

	"github.com/astrovox/astrovox/tensor"
)

// TestBoundary_AllDtypesConstructors exercises New, Zeros,
// Ones, and Full across every supported dtype.
func TestBoundary_AllDtypesConstructors(t *testing.T) {
	for d := tensor.DType(0); int(d) < int(tensor.NumDTypes); d++ {
		for _, ctor := range []struct {
			name string
			fn   func() (*tensor.Tensor, error)
		}{
			{"New", func() (*tensor.Tensor, error) { return tensor.New(d, []int{2, 2}) }},
			{"Zeros", func() (*tensor.Tensor, error) { return tensor.Zeros(d, []int{2, 2}) }},
			{"Ones", func() (*tensor.Tensor, error) { return tensor.Ones(d, []int{2, 2}) }},
			{"Full", func() (*tensor.Tensor, error) { return tensor.Full(d, []int{2, 2}, 1.5) }},
		} {
			src, err := ctor.fn()
			if err != nil {
				t.Fatalf("%s(%s): %v", ctor.name, d, err)
			}
			if src.DType() != d {
				t.Fatalf("%s(%s): dtype = %s", ctor.name, d, src.DType())
			}
			if src.NumElements() != 4 {
				t.Fatalf("%s(%s): elements = %d, want 4", ctor.name, d, src.NumElements())
			}
		}
	}
}

// TestBoundary_EmptyTensor covers zero-sized dimensions.
func TestBoundary_EmptyTensor(t *testing.T) {
	src, err := tensor.Zeros(tensor.Float32, []int{0, 3})
	if err != nil {
		t.Fatal(err)
	}
	if src.NumElements() != 0 {
		t.Fatalf("empty tensor elements = %d, want 0", src.NumElements())
	}
	data, err := tensor.Save(src)
	if err != nil {
		t.Fatal(err)
	}
	loaded, err := tensor.Load(data)
	if err != nil {
		t.Fatal(err)
	}
	if loaded.NumElements() != 0 {
		t.Fatalf("round-trip empty elements = %d, want 0", loaded.NumElements())
	}
}

// TestBoundary_SingleElement covers 1-element tensors.
func TestBoundary_SingleElement(t *testing.T) {
	for d := tensor.DType(0); int(d) < int(tensor.NumDTypes); d++ {
		src, err := tensor.Full(d, []int{1}, 7.0)
		if err != nil {
			t.Fatalf("Full(%s): %v", d, err)
		}
		v, err := src.Get(0)
		if err != nil {
			t.Fatalf("Get(%s): %v", d, err)
		}
		if v == nil {
			t.Fatalf("Get(%s) = nil", d)
		}
	}
}

// TestBoundary_Scalar covers rank-0 tensors.
func TestBoundary_Scalar(t *testing.T) {
	src, err := tensor.Full(tensor.Float64, nil, 3.25)
	if err != nil {
		t.Fatal(err)
	}
	if !src.Shape().IsScalar() {
		t.Fatal("scalar shape is not scalar")
	}
	if src.NumElements() != 1 {
		t.Fatalf("scalar elements = %d, want 1", src.NumElements())
	}
	v, err := src.Get()
	if err != nil {
		t.Fatal(err)
	}
	if v.(float64) != 3.25 {
		t.Fatalf("scalar value = %v, want 3.25", v)
	}
}

// TestBoundary_ExtremeValues covers min/max numeric values
// through the cast and saturation paths.
func TestBoundary_ExtremeValues(t *testing.T) {
	cases := []struct {
		dt   tensor.DType
		v    float64
		want int64
	}{
		{tensor.Int8, 1e9, math.MaxInt8},
		{tensor.Int8, -1e9, math.MinInt8},
		{tensor.Int16, 1e9, math.MaxInt16},
		{tensor.Int16, -1e9, math.MinInt16},
		{tensor.Int32, 1e18, math.MaxInt32},
		{tensor.Int32, -1e18, math.MinInt32},
		{tensor.Int64, 1e18, int64(1e18)},
		{tensor.Int64, -1e18, int64(-1e18)},
		{tensor.Uint8, 1e9, math.MaxUint8},
		{tensor.Uint8, -1e9, 0},
		{tensor.Uint16, 1e9, math.MaxUint16},
		{tensor.Uint32, 1e18, math.MaxUint32},
	}
	for _, tc := range cases {
		got := toInt64(tc.dt.Cast(tc.v))
		if got != tc.want {
			t.Errorf("Cast(%s, %v) = %d, want %d", tc.dt, tc.v, got, tc.want)
		}
	}
	// Uint64 saturates at the unsigned 64-bit maximum.
	if got := tensor.Uint64.Cast(1e20).(uint64); got != math.MaxUint64 {
		t.Errorf("Cast(uint64, 1e20) = %d, want %d", got, uint64(math.MaxUint64))
	}
	if got := tensor.Uint64.Cast(1e18).(uint64); got != uint64(1e18) {
		t.Errorf("Cast(uint64, 1e18) = %d, want %d", got, uint64(1e18))
	}
	if got := tensor.Uint64.Cast(-1e18).(uint64); got != 0 {
		t.Errorf("Cast(uint64, -1e18) = %d, want 0", got)
	}
}

// toInt64 widens any integer cast result to int64.
func toInt64(v any) int64 {
	switch x := v.(type) {
	case int8:
		return int64(x)
	case int16:
		return int64(x)
	case int32:
		return int64(x)
	case int64:
		return x
	case uint8:
		return int64(x)
	case uint16:
		return int64(x)
	case uint32:
		return int64(x)
	default:
		panic(fmt.Sprintf("unexpected integer type %T", v))
	}
}

// TestBoundary_BoolCast covers boolean coercion.
func TestBoundary_BoolCast(t *testing.T) {
	if v := tensor.Bool.Cast(0).(bool); v {
		t.Error("Bool.Cast(0) = true, want false")
	}
	if v := tensor.Bool.Cast(1).(bool); !v {
		t.Error("Bool.Cast(1) = false, want true")
	}
	if v := tensor.Bool.Cast(-1).(bool); !v {
		t.Error("Bool.Cast(-1) = false, want true")
	}
}

// TestBoundary_NanCast covers NaN coercion to zero.
func TestBoundary_NanCast(t *testing.T) {
	for _, d := range []tensor.DType{tensor.Int8, tensor.Int16, tensor.Int32, tensor.Int64} {
		got := toInt64(d.Cast(math.NaN()))
		if got != 0 {
			t.Errorf("Cast(%s, NaN) = %d, want 0", d, got)
		}
	}
}

// TestRegression_SmallTensorRoundTrip guards the Load
// length-check bug: streams smaller than header+rank*24
// must load (payload may be empty or tiny).
func TestRegression_SmallTensorRoundTrip(t *testing.T) {
	cases := []struct {
		dtype tensor.DType
		dims  []int
	}{
		{tensor.Float32, []int{1}},
		{tensor.Float32, []int{2}},
		{tensor.Float64, []int{1}},
		{tensor.Int8, []int{1}},
		{tensor.Bool, []int{4}},
		{tensor.Float32, []int{0, 3}},
		{tensor.Complex64, []int{1}},
	}
	for _, tc := range cases {
		src, err := tensor.Zeros(tc.dtype, tc.dims)
		if err != nil {
			t.Fatalf("Zeros(%s, %v): %v", tc.dtype, tc.dims, err)
		}
		data, err := tensor.Save(src)
		if err != nil {
			t.Fatalf("Save(%s, %v): %v", tc.dtype, tc.dims, err)
		}
		loaded, err := tensor.Load(data)
		if err != nil {
			t.Fatalf("Load(%s, %v): %v", tc.dtype, tc.dims, err)
		}
		eq, err := src.Equal(loaded)
		if err != nil {
			t.Fatalf("Equal(%s, %v): %v", tc.dtype, tc.dims, err)
		}
		if !eq {
			t.Fatalf("round-trip mismatch for %s %v", tc.dtype, tc.dims)
		}
	}
}

// TestBoundary_ArangeEdgeCases covers empty and negative
// step aranges.
func TestBoundary_ArangeEdgeCases(t *testing.T) {
	if _, err := tensor.Arange(tensor.Float32, 0, 0, 1); err != nil {
		t.Fatalf("empty arange: %v", err)
	}
	if _, err := tensor.Arange(tensor.Float32, 0, 10, 0); err == nil {
		t.Fatal("zero step arange: expected error")
	}
	src, err := tensor.Arange(tensor.Float64, 10, 0, -2)
	if err != nil {
		t.Fatal(err)
	}
	if src.NumElements() != 5 {
		t.Fatalf("negative-step arange elements = %d, want 5", src.NumElements())
	}
}

// TestBoundary_SliceEdges covers empty and full slices.
func TestBoundary_SliceEdges(t *testing.T) {
	src, err := tensor.Ones(tensor.Float32, []int{4, 4})
	if err != nil {
		t.Fatal(err)
	}
	empty, err := src.Slice([]int{0, 0}, []int{0, 4})
	if err != nil {
		t.Fatal(err)
	}
	if empty.NumElements() != 0 {
		t.Fatalf("empty slice elements = %d, want 0", empty.NumElements())
	}
	full, err := src.Slice([]int{0, 0}, []int{4, 4})
	if err != nil {
		t.Fatal(err)
	}
	eq, err := src.Equal(full)
	if err != nil {
		t.Fatal(err)
	}
	if !eq {
		t.Fatal("full slice != original")
	}
}
