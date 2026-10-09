// Package math provides mixed precision and quantized kernels.
package math

import (
	"math"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
)

// Float16 represents a 16-bit floating point value (IEEE 754 binary16).
type Float16 uint16

// Float32 represents a 32-bit floating point value.
type Float32 float32

// BFloat16 represents a 16-bit brain floating point value.
type BFloat16 uint16

// Float16bits converts float32 to Float16 bits.
func Float16bits(f float32) Float16 {
	// Simplified: in production use math.Float32bits/frombits
	return Float16(math.Float32bits(f) >> 16)
}

// Float32frombits converts Float16 bits to float32.
func Float32frombits(h Float16) float32 {
	return math.Float32frombits(uint32(h) << 16)
}

// BFloat16bits converts float32 to BFloat16 bits.
func BFloat16bits(f float32) BFloat16 {
	return BFloat16(math.Float32bits(f) >> 16)
}

// BFloat32frombits converts BFloat16 bits to float32.
func BFloat32frombits(h BFloat16) float32 {
	return math.Float32frombits(uint32(h) << 16)
}

// MixedPrecisionGEMM computes C = A @ B with mixed precision.
// A: [M, K] float16/bfloat16, B: [K, N] float16/bfloat16
// Accumulation in float32, output in float16/bfloat16/float32.
func MixedPrecisionGEMM(A, B *tensor.Tensor, out *tensor.Tensor, accumulateInFP32 bool) error {
	if A == nil || B == nil || out == nil {
		return errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	// For now, implement with float64 simulation
	// Real implementation would use float16/bfloat16 storage with float32 accumulation
	return GEMM(false, false, 1, A, B, 0, out)
}

// QuantizationScheme defines the quantization parameters.
type QuantizationScheme int

const (
	QuantPerTensor QuantizationScheme = iota
	QuantPerChannel
	QuantPerGroup
)

// QParams holds quantization parameters.
type QParams struct {
	Scale     float64
	ZeroPoint int
	Min       float64
	Max       float64
	Scheme    QuantizationScheme
	GroupSize int // For per-group quantization
}

// QuantizeInt8 quantizes a float64 tensor to int8.
// Uses symmetric quantization by default.
func QuantizeInt8(x *tensor.Tensor, params *QParams) (*tensor.Tensor, error) {
	if x == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.DType() != tensor.Float64 {
		return nil, errors.New(errors.CodeDTypeMismatch, "quantize requires float64 input")
	}

	// Determine scale/zero_point if not provided
	scale := params.Scale
	zp := params.ZeroPoint

	if scale == 0 {
		// Compute from data
		xv := x.Float64()
		var minVal, maxVal float64 = xv[0], xv[0]
		for _, v := range xv {
			if v < minVal {
				minVal = v
			}
			if v > maxVal {
				maxVal = v
			}
		}
		if params.Scheme == QuantPerTensor {
			scale = max(maxVal, -minVal) / 127.0
			if scale == 0 {
				scale = 1.0
			}
			zp = 0
		}
	}

	out, err := tensor.New(tensor.Int8, x.Shape().Dims())
	if err != nil {
		return nil, err
	}

	xv := x.Float64()
	ov := out.Int8()

	for i := range xv {
		q := int(math.Round(xv[i]/scale)) + zp
		if q < -128 {
			q = -128
		} else if q > 127 {
			q = 127
		}
		ov[i] = int8(q)
	}

	return out, nil
}

// DequantizeInt8 dequantizes an int8 tensor to float64.
func DequantizeInt8(x *tensor.Tensor, params *QParams) (*tensor.Tensor, error) {
	if x == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.DType() != tensor.Int8 {
		return nil, errors.New(errors.CodeDTypeMismatch, "dequantize requires int8 input")
	}

	scale := params.Scale
	zp := params.ZeroPoint
	if scale == 0 {
		return nil, errors.New(errors.CodeInvalidArgument, "scale not provided")
	}

	out, err := tensor.New(tensor.Float64, x.Shape().Dims())
	if err != nil {
		return nil, err
	}

	xv := x.Int8()
	ov := out.Float64()

	for i := range xv {
		ov[i] = float64(xv[i]-int8(zp)) * scale
	}

	return out, nil
}

// QuantizeInt4 quantizes a float64 tensor to int4 (packed two per byte).
func QuantizeInt4(x *tensor.Tensor, params *QParams) (*tensor.Tensor, error) {
	if x == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.DType() != tensor.Float64 {
		return nil, errors.New(errors.CodeDTypeMismatch, "quantize requires float64 input")
	}

	numel := x.NumElements()
	if numel%2 != 0 {
		return nil, errors.New(errors.CodeInvalidArgument, "int4 requires even number of elements")
	}

	scale := params.Scale
	zp := params.ZeroPoint

	if scale == 0 {
		xv := x.Float64()
		var minVal, maxVal float64 = xv[0], xv[0]
		for _, v := range xv {
			if v < minVal {
				minVal = v
			}
			if v > maxVal {
				maxVal = v
			}
		}
		scale = max(maxVal, -minVal) / 7.0
		if scale == 0 {
			scale = 1.0
		}
		zp = 8 // Centered for unsigned-like packing
	}

	// Output has half the elements (2 int4 per byte)
	outShape := make([]int, len(x.Shape().Dims()))
	copy(outShape, x.Shape().Dims())
	outShape[len(outShape)-1] /= 2

	out, err := tensor.New(tensor.Int8, outShape) // Packed in int8
	if err != nil {
		return nil, err
	}

	xv := x.Float64()
	ov := out.Int8()

	for i := 0; i < numel; i += 2 {
		q1 := int(math.Round(xv[i]/scale)) + zp
		q2 := int(math.Round(xv[i+1]/scale)) + zp

		// Clamp to [-8, 7] for signed int4
		if q1 < -8 {
			q1 = -8
		} else if q1 > 7 {
			q1 = 7
		}
		if q2 < -8 {
			q2 = -8
		} else if q2 > 7 {
			q2 = 7
		}

		// Pack: q1 in low 4 bits, q2 in high 4 bits (or vice versa)
		packed := int8((q1 & 0xF) | ((q2 & 0xF) << 4))
		ov[i/2] = packed
	}

	return out, nil
}

// DequantizeInt4 dequantizes a packed int4 tensor to float64.
func DequantizeInt4(x *tensor.Tensor, params *QParams) (*tensor.Tensor, error) {
	if x == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.DType() != tensor.Int8 {
		return nil, errors.New(errors.CodeDTypeMismatch, "dequantize requires int8 (packed int4) input")
	}

	scale := params.Scale
	zp := params.ZeroPoint
	if scale == 0 {
		return nil, errors.New(errors.CodeInvalidArgument, "scale not provided")
	}

	outShape := make([]int, len(x.Shape().Dims()))
	copy(outShape, x.Shape().Dims())
	outShape[len(outShape)-1] *= 2

	out, err := tensor.New(tensor.Float64, outShape)
	if err != nil {
		return nil, err
	}

	xv := x.Int8()
	ov := out.Float64()

	for i := 0; i < x.NumElements(); i++ {
		packed := xv[i]
		q1 := int(packed & 0xF)
		q2 := int((packed >> 4) & 0xF)

		// Sign extend for signed int4
		if q1 >= 8 {
			q1 -= 16
		}
		if q2 >= 8 {
			q2 -= 16
		}

		ov[2*i] = float64(q1-zp) * scale
		ov[2*i+1] = float64(q2-zp) * scale
	}

	return out, nil
}

// Int8GEMM computes C = A @ B with int8 inputs and int32 accumulation.
// A: [M, K] int8, B: [K, N] int8, C: [M, N] int32
// Requires quantization scales for A, B and output scale for C.
func Int8GEMM(A, B *tensor.Tensor, out *tensor.Tensor,
	scaleA, scaleB, scaleOut float64, zpA, zpB, zpOut int32) error {
	if A == nil || B == nil || out == nil {
		return errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if A.DType() != tensor.Int8 || B.DType() != tensor.Int8 || out.DType() != tensor.Int32 {
		return errors.New(errors.CodeDTypeMismatch, "int8 gemm requires int8/int8/int32")
	}
	if A.Shape().Rank() != 2 || B.Shape().Rank() != 2 || out.Shape().Rank() != 2 {
		return errors.New(errors.CodeInvalidArgument, "requires 2-D tensors")
	}

	M, K := A.Shape().Dim(0), A.Shape().Dim(1)
	KB, N := B.Shape().Dim(0), B.Shape().Dim(1)
	if K != KB {
		return errors.New(errors.CodeShapeMismatch, "contracting dims mismatch")
	}
	if out.Shape().Dim(0) != M || out.Shape().Dim(1) != N {
		return errors.New(errors.CodeShapeMismatch, "output shape mismatch")
	}

	av := A.Int8()
	bv := B.Int8()
	cv := out.Int32()

	// Int8 GEMM with int32 accumulation
	for i := 0; i < M; i++ {
		for j := 0; j < N; j++ {
			var acc int32
			for k := 0; k < K; k++ {
				a := int32(av[i*K+k]) - zpA
				b := int32(bv[k*N+j]) - zpB
				acc += a * b
			}
			// Apply output scaling: scaleA * scaleB / scaleOut
			// Simplified: assume scaleOut = scaleA * scaleB
			cv[i*N+j] = acc + zpOut
		}
	}

	return nil
}

// Int4GEMM computes C = A @ B with packed int4 inputs.
// A: [M, K] packed int4, B: [K, N] packed int4, C: [M, N] int32
func Int4GEMM(A, B *tensor.Tensor, out *tensor.Tensor,
	scaleA, scaleB, scaleOut float64, zpA, zpB, zpOut int32) error {
	// Similar to Int8GEMM but with unpacking
	// For brevity, delegate to Int8GEMM after dequantization
	return errors.New(errors.CodeUnimplemented, "int4 gemm not yet implemented")
}

// QuantizedLinear applies quantized linear transformation.
// Input: int8 quantized, Weight: int8 quantized, Bias: float64
// Output: float64
func QuantizedLinear(x, W *tensor.Tensor, b *tensor.Tensor,
	xParams, wParams *QParams, out *tensor.Tensor) error {
	if x == nil || W == nil || out == nil {
		return errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	// Dequantize to float64 for now
	xF, err := DequantizeInt8(x, xParams)
	if err != nil {
		return err
	}
	WF, err := DequantizeInt8(W, wParams)
	if err != nil {
		return err
	}
	return GEMM(false, false, 1, xF, WF, 0, out)
}

// AutoQuantize finds optimal quantization parameters for a tensor.
func AutoQuantize(x *tensor.Tensor, scheme QuantizationScheme, groupSize int) (*QParams, error) {
	if x == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.DType() != tensor.Float64 {
		return nil, errors.New(errors.CodeDTypeMismatch, "requires float64")
	}

	xv := x.Float64()

	if scheme == QuantPerTensor {
		var minVal, maxVal float64 = xv[0], xv[0]
		for _, v := range xv {
			if v < minVal {
				minVal = v
			}
			if v > maxVal {
				maxVal = v
			}
		}
		scale := max(maxVal, -minVal) / 127.0
		if scale == 0 {
			scale = 1.0
		}
		return &QParams{
			Scale:     scale,
			ZeroPoint: 0,
			Min:       minVal,
			Max:       maxVal,
			Scheme:    scheme,
		}, nil
	}

	// Per-channel or per-group quantization
	// Would implement per-channel/group statistics
	return &QParams{
		Scale:     1.0,
		ZeroPoint: 0,
		Scheme:    scheme,
		GroupSize: groupSize,
	}, nil
}