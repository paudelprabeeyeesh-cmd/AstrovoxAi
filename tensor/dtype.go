package tensor

import (
	"fmt"
	"math"
	"math/bits"

	"github.com/astrovox/astrovox/internal/errors"
)

// DType enumerates supported tensor data types. The numeric
// values are part of the serialization format contract.
type DType int

// Supported data types.
const (
	Bool DType = iota
	Int8
	Int16
	Int32
	Int64
	Uint8
	Uint16
	Uint32
	Uint64
	Float16
	BFloat16
	Float32
	Float64
	Complex64
	Complex128
	NumDTypes
)

var dtypeNames = [...]string{
	Bool:       "bool",
	Int8:       "int8",
	Int16:      "int16",
	Int32:      "int32",
	Int64:      "int64",
	Uint8:      "uint8",
	Uint16:     "uint16",
	Uint32:     "uint32",
	Uint64:     "uint64",
	Float16:    "float16",
	BFloat16:   "bfloat16",
	Float32:    "float32",
	Float64:    "float64",
	Complex64:  "complex64",
	Complex128: "complex128",
}

var dtypeSizes = [...]int{
	Bool:       1,
	Int8:       1,
	Int16:      2,
	Int32:      4,
	Int64:      8,
	Uint8:      1,
	Uint16:     2,
	Uint32:     4,
	Uint64:     8,
	Float16:    2,
	BFloat16:   2,
	Float32:    4,
	Float64:    8,
	Complex64:  8,
	Complex128: 16,
}

// String returns the canonical dtype name.
func (d DType) String() string {
	if d < 0 || int(d) >= int(NumDTypes) {
		return fmt.Sprintf("dtype(%d)", int(d))
	}
	return dtypeNames[d]
}

// Size returns the byte size of one element.
func (d DType) Size() int {
	if d < 0 || int(d) >= int(NumDTypes) {
		return 0
	}
	return dtypeSizes[d]
}

// IsFloat reports whether the dtype is floating point.
func (d DType) IsFloat() bool {
	switch d {
	case Float16, BFloat16, Float32, Float64:
		return true
	default:
		return false
	}
}

// IsComplex reports whether the dtype is complex.
func (d DType) IsComplex() bool { return d == Complex64 || d == Complex128 }

// IsInteger reports whether the dtype is a fixed-width integer.
func (d DType) IsInteger() bool {
	switch d {
	case Int8, Int16, Int32, Int64, Uint8, Uint16, Uint32, Uint64:
		return true
	default:
		return false
	}
}

// IsSigned reports whether integer values are signed.
func (d DType) IsSigned() bool {
	switch d {
	case Int8, Int16, Int32, Int64:
		return true
	default:
		return false
	}
}

// ParseDType resolves a dtype by canonical name.
func ParseDType(name string) (DType, error) {
	for d := DType(0); int(d) < int(NumDTypes); d++ {
		if dtypeNames[d] == name {
			return d, nil
		}
	}
	return 0, errors.New(errors.CodeInvalidArgument, "unknown dtype").
		WithField("name", name)
}

// Promote returns the smallest dtype that can represent values
// of both a and b without loss (promotion lattice).
func Promote(a, b DType) DType {
	if a == b {
		return a
	}
	if a.IsComplex() || b.IsComplex() {
		return Complex128
	}
	if a.IsFloat() || b.IsFloat() {
		return promoteFloat(a, b)
	}
	return promoteInteger(a, b)
}

func promoteFloat(a, b DType) DType {
	rank := func(d DType) int {
		switch d {
		case Float16, BFloat16:
			return 1
		case Float32:
			return 2
		case Float64:
			return 3
		default:
			return 0
		}
	}
	ra, rb := rank(a), rank(b)
	if ra >= rb && ra >= 2 {
		if ra == 3 {
			return Float64
		}
		return Float32
	}
	if rb >= 2 {
		if rb == 3 {
			return Float64
		}
		return Float32
	}
	return Float32
}

func promoteInteger(a, b DType) DType {
	ra := intRank(a)
	rb := intRank(b)
	if ra >= rb {
		return a
	}
	return b
}

func intRank(d DType) int {
	switch d {
	case Bool:
		return 0
	case Int8, Uint8:
		return 1
	case Int16, Uint16:
		return 2
	case Int32, Uint32:
		return 3
	case Int64, Uint64:
		return 4
	default:
		return -1
	}
}

// Cast converts a float64 value to the dtype with
// round-to-nearest-even and saturation policies.
func (d DType) Cast(v float64) any {
	switch d {
	case Bool:
		return v != 0
	case Int8:
		return int8(saturate(v, math.MinInt8, math.MaxInt8))
	case Int16:
		return int16(saturate(v, math.MinInt16, math.MaxInt16))
	case Int32:
		return int32(saturate(v, math.MinInt32, math.MaxInt32))
	case Int64:
		return int64(saturate(v, math.MinInt64, math.MaxInt64))
	case Uint8:
		return uint8(saturate(v, 0, math.MaxUint8))
	case Uint16:
		return uint16(saturate(v, 0, math.MaxUint16))
	case Uint32:
		return uint32(saturate(v, 0, math.MaxUint32))
	case Uint64:
		return uint64(saturate(v, 0, math.MaxUint64))
	case Float16:
		return Float16bits(float32(v))
	case BFloat16:
		return BFloat16bits(float32(v))
	case Float32:
		return float32(v)
	case Float64:
		return v
	case Complex64:
		return complex(float32(v), 0)
	case Complex128:
		return complex(v, 0)
	default:
		return v
	}
}

func saturate(v, lo, hi float64) float64 {
	if math.IsNaN(v) {
		return 0
	}
	if v < lo {
		return lo
	}
	if v > hi {
		return hi
	}
	return v
}

// Float16bits converts a float32 to IEEE 754 binary16 bits
// with round-to-nearest-even.
func Float16bits(f float32) uint16 {
	u := math.Float32bits(f)
	sign := (u >> 16) & 0x8000
	exp := int((u >> 23) & 0xFF)
	mant := u & 0x7FFFFF
	if exp == 0xFF {
		if mant != 0 {
			return uint16(sign | 0x7E00)
		}
		return uint16(sign | 0x7C00)
	}
	e := exp - 127 + 15
	if e <= 0 {
		if e < -10 {
			return uint16(sign)
		}
		mant |= 1 << 23
		shift := uint(14 - e)
		round := uint32(1) << (shift - 1)
		m := (mant + round) >> shift
		if m == 1<<10 {
			return uint16(sign | 0x400)
		}
		return uint16(sign | m)
	}
	if e >= 31 {
		return uint16(sign | 0x7C00)
	}
	round := uint32(0x1000)
	if mant&0xFFF == 0x800 && (mant>>12)&1 == 0 {
		round = 0
	}
	m := (mant + round) >> 12
	if m == 1<<10 {
		return uint16(sign | 0x7C00)
	}
	return uint16(sign | uint32(e)<<10 | (m & 0x3FF))
}

// BFloat16bits converts a float32 to bfloat16 bits with
// round-to-nearest-even.
func BFloat16bits(f float32) uint16 {
	u := math.Float32bits(f)
	round := uint32(0x8000)
	if u&0x7FFF == 0x4000 && (u>>16)&1 == 0 {
		round = 0
	}
	return uint16((u + round) >> 16)
}

// Float16Value converts IEEE 754 binary16 bits to float32.
func Float16Value(b uint16) float32 {
	sign := uint32(b>>15) << 31
	exp := int((b >> 10) & 0x1F)
	mant := uint32(b & 0x3FF)
	var u uint32
	switch {
	case exp == 0:
		if mant == 0 {
			u = sign
		} else {
			lz := bits.LeadingZeros32(mant)
			j := uint(lz - 8)
			expField := 134 - lz
			frac := int64(mant)<<j - (1 << 23)
			u = sign | uint32(expField)<<23 | uint32(frac)
		}
	case exp == 31:
		u = sign | 0x7F800000 | (mant << 13)
	default:
		u = sign | uint32(exp-15+127)<<23 | (mant << 13)
	}
	return math.Float32frombits(u)
}

// BFloat16Value converts bfloat16 bits to float32.
func BFloat16Value(bits uint16) float32 {
	return math.Float32frombits(uint32(bits) << 16)
}
