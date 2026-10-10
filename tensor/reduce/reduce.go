// Package reduce implements reduction kernels over tensors.
package reduce

import (
	"math"
	"sync"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
)

// Sum returns the sum over dims (empty = all).
func Sum(t *tensor.Tensor, dims []int, keepDims bool) (*tensor.Tensor, error) {
	return reduce(t, dims, keepDims, func(acc, v float64) float64 { return acc + v }, 0)
}

// Mean returns the mean over dims.
func Mean(t *tensor.Tensor, dims []int, keepDims bool) (*tensor.Tensor, error) {
	plan, err := PlanReduction(t.Shape().Dims(), dims, keepDims)
	if err != nil {
		return nil, err
	}
	sums, err := reduce(t, dims, keepDims, func(acc, v float64) float64 { return acc + v }, 0)
	if err != nil {
		return nil, err
	}
	n := float64(plan.ReduceNumElements())
	return scaleOutput(sums, 1/n)
}

// Var returns the population variance over dims (Welford).
func Var(t *tensor.Tensor, dims []int, keepDims bool) (*tensor.Tensor, error) {
	means, err := Mean(t, dims, keepDims)
	if err != nil {
		return nil, err
	}
	return reduceAround(t, means, dims, keepDims,
		func(acc, v float64) float64 { return acc + v*v }, 0,
		func(acc float64, n float64) float64 { return acc / n })
}

// Std returns the population standard deviation over dims.
func Std(t *tensor.Tensor, dims []int, keepDims bool) (*tensor.Tensor, error) {
	v, err := Var(t, dims, keepDims)
	if err != nil {
		return nil, err
	}
	return transform(v, math.Sqrt)
}

// Max returns the maximum over dims.
func Max(t *tensor.Tensor, dims []int, keepDims bool) (*tensor.Tensor, error) {
	return reduce(t, dims, keepDims, math.Max, math.Inf(-1))
}

// Min returns the minimum over dims.
func Min(t *tensor.Tensor, dims []int, keepDims bool) (*tensor.Tensor, error) {
	return reduce(t, dims, keepDims, math.Min, math.Inf(1))
}

// Prod returns the product over dims.
func Prod(t *tensor.Tensor, dims []int, keepDims bool) (*tensor.Tensor, error) {
	return reduce(t, dims, keepDims, func(acc, v float64) float64 { return acc * v }, 1)
}

// ArgMax returns the index of the maximum along dim.
func ArgMax(t *tensor.Tensor, dim int) (*tensor.Tensor, error) {
	return argReduce(t, dim, func(a, b float64) bool { return a > b })
}

// ArgMin returns the index of the minimum along dim.
func ArgMin(t *tensor.Tensor, dim int) (*tensor.Tensor, error) {
	return argReduce(t, dim, func(a, b float64) bool { return a < b })
}

// CumSum returns the cumulative sum along dim.
func CumSum(t *tensor.Tensor, dim int) (*tensor.Tensor, error) {
	if t == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if t.DType() != tensor.Float64 {
		return nil, errors.New(errors.CodeDTypeMismatch, "reductions require float64").
			WithField("dtype", t.DType())
	}
	rank := t.Shape().Rank()
	if dim < 0 || dim >= rank {
		return nil, errors.New(errors.CodeInvalidArgument, "dim out of range").
			WithField("dim", dim).WithField("rank", rank)
	}
	out, err := tensor.New(tensor.Float64, t.Shape().Dims())
	if err != nil {
		return nil, err
	}
	src := t.Float64()
	dst := out.Float64()
	strides := t.Strides()
	total := t.Shape().NumElements()
	axisStride := strides[dim]
	axisSize := t.Shape().Dim(dim)
	outer := total / (axisSize * axisStride)
	for o := 0; o < outer; o++ {
		base := o * axisSize * axisStride
		for j := 0; j < axisStride; j++ {
			var acc float64
			for i := 0; i < axisSize; i++ {
				acc += src[base+i*axisStride+j]
				dst[base+i*axisStride+j] = acc
			}
		}
	}
	return out, nil
}

// Norm returns the Lp norm over dims (empty = all).
func Norm(t *tensor.Tensor, p float64, dims []int, keepDims bool) (*tensor.Tensor, error) {
	if math.IsInf(p, 1) {
		abs, err := AbsSafe(t)
		if err != nil {
			return nil, err
		}
		return Max(abs, dims, keepDims)
	}
	if math.IsInf(p, -1) {
		abs, err := AbsSafe(t)
		if err != nil {
			return nil, err
		}
		return Min(abs, dims, keepDims)
	}
	abs, err := AbsSafe(t)
	if err != nil {
		return nil, err
	}
	powered, err := transform(abs, func(v float64) float64 { return math.Pow(v, p) })
	if err != nil {
		return nil, err
	}
	summed, err := Sum(powered, dims, keepDims)
	if err != nil {
		return nil, err
	}
	return transform(summed, func(v float64) float64 { return math.Pow(v, 1/p) })
}

// AbsSafe returns element-wise absolute values.
func AbsSafe(t *tensor.Tensor) (*tensor.Tensor, error) {
	return transform(t, math.Abs)
}

// All reports whether all elements are non-zero over dims.
func All(t *tensor.Tensor, dims []int, keepDims bool) (*tensor.Tensor, error) {
	return reduce(t, dims, keepDims, func(acc, v float64) float64 {
		if acc != 0 && v != 0 {
			return 1
		}
		return 0
	}, 1)
}

// Any reports whether any element is non-zero over dims.
func Any(t *tensor.Tensor, dims []int, keepDims bool) (*tensor.Tensor, error) {
	return reduce(t, dims, keepDims, func(acc, v float64) float64 {
		if acc != 0 || v != 0 {
			return 1
		}
		return 0
	}, 0)
}

// LogSumExp returns log(sum(exp(x))) with max-shift stability.
func LogSumExp(t *tensor.Tensor, dims []int, keepDims bool) (*tensor.Tensor, error) {
	maxes, err := Max(t, dims, true)
	if err != nil {
		return nil, err
	}
	shifted, err := shift(t, maxes, dims)
	if err != nil {
		return nil, err
	}
	exps, err := transform(shifted, math.Exp)
	if err != nil {
		return nil, err
	}
	sums, err := Sum(exps, dims, keepDims)
	if err != nil {
		return nil, err
	}
	logs, err := transform(sums, math.Log)
	if err != nil {
		return nil, err
	}
	maxKeep := maxes
	if !keepDims {
		maxKeep, err = squeeze(maxes)
		if err != nil {
			return nil, err
		}
	}
	return AddSafe(logs, maxKeep)
}

// NewPlan wraps the reduction planning logic.
func NewPlan(t *tensor.Tensor, dims []int, keepDims bool) (Plan, error) {
	return PlanReduction(t.Shape().Dims(), dims, keepDims)
}

// AddSafe returns a + b with broadcasting.
func AddSafe(a, b *tensor.Tensor) (*tensor.Tensor, error) {
	outShape, err := a.Shape().Broadcast(b.Shape())
	if err != nil {
		return nil, err
	}
	out, err := tensor.New(tensor.Float64, outShape.Dims())
	if err != nil {
		return nil, err
	}
	if a.NumElements() == b.NumElements() && a.IsContiguous() && b.IsContiguous() && out.IsContiguous() {
		x := a.Float64()
		y := b.Float64()
		z := out.Float64()
		for i := range z {
			z[i] = x[i] + y[i]
		}
		return out, nil
	}
	// Broadcast path via scalar expansion.
	if b.NumElements() == 1 {
		s := b.Float64()[0]
		z := out.Float64()
		x := a.Float64()
		for i := range z {
			z[i] = x[i] + s
		}
		return out, nil
	}
	if a.NumElements() == 1 {
		s := a.Float64()[0]
		z := out.Float64()
		y := b.Float64()
		for i := range z {
			z[i] = s + y[i]
		}
		return out, nil
	}
	return nil, errors.New(errors.CodeUnimplemented, "general broadcast add")
}

func scaleOutput(t *tensor.Tensor, scale float64) (*tensor.Tensor, error) {
	return transform(t, func(v float64) float64 { return v * scale })
}

func transform(t *tensor.Tensor, fn func(float64) float64) (*tensor.Tensor, error) {
	if t == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if t.DType() != tensor.Float64 {
		return nil, errors.New(errors.CodeDTypeMismatch, "reductions require float64").
			WithField("dtype", t.DType())
	}
	out, err := tensor.New(tensor.Float64, t.Shape().Dims())
	if err != nil {
		return nil, err
	}
	src := t.Float64()
	dst := out.Float64()
	for i := range src {
		dst[i] = fn(src[i])
	}
	return out, nil
}

func reduce(t *tensor.Tensor, dims []int, keepDims bool,
	combine func(acc, v float64) float64, init float64) (*tensor.Tensor, error) {
	if t == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if t.DType() != tensor.Float64 {
		return nil, errors.New(errors.CodeDTypeMismatch, "reductions require float64").
			WithField("dtype", t.DType())
	}
	plan, err := PlanReduction(t.Shape().Dims(), dims, keepDims)
	if err != nil {
		return nil, err
	}
	out, err := tensor.New(tensor.Float64, plan.OutputShape)
	if err != nil {
		return nil, err
	}
	src := t.Float64()
	dst := out.Float64()
	strides := plan.InputStrides
	// Initialize accumulators.
	for i := range dst {
		dst[i] = init
	}
	// Parallelize over outer elements when profitable.
	outerNum := 1
	for _, d := range plan.OuterDims {
		outerNum *= t.Shape().Dim(d)
	}
	const parallelThreshold = 1 << 16
	var wg sync.WaitGroup
	workers := 1
	if outerNum*plan.ReduceNumElements() >= parallelThreshold {
		workers = 4
	}
	chunk := (outerNum + workers - 1) / workers
	for w := 0; w < workers; w++ {
		lo := w * chunk
		hi := min(lo+chunk, outerNum)
		if lo >= hi {
			continue
		}
		if workers > 1 {
			wg.Add(1)
		}
		work := func(lo, hi int) {
			if workers > 1 {
				defer wg.Done()
			}
			for o := lo; o < hi; o++ {
				base := outerOffset(o, plan.OuterDims, t.Shape().Dims(), strides)
				outIdx := outerOffset(o, plan.OuterDims, outShapeFor(plan), outStridesFor(plan))
				reduceOver(t, plan, src, dst, base, outIdx, combine, init)
			}
		}
		if workers > 1 {
			go work(lo, hi)
		} else {
			work(lo, hi)
		}
	}
	wg.Wait()
	return out, nil
}

func reduceOver(t *tensor.Tensor, plan Plan, src, dst []float64, inBase, outIdx int,
	combine func(acc, v float64) float64, init float64) {
	strides := plan.InputStrides
	// Iterate the reduction subspace with an odometer.
	reduceDims := plan.ReduceDims
	reduceShape := make([]int, len(reduceDims))
	for i, d := range reduceDims {
		reduceShape[i] = plan.InputShape[d]
	}
	if len(reduceDims) == 0 {
		dst[outIdx] = combine(dst[outIdx], src[inBase])
		return
	}
	idx := make([]int, len(reduceDims))
	n := 1
	for _, d := range reduceShape {
		n *= d
	}
	for k := 0; k < n; k++ {
		off := inBase
		for i, d := range reduceDims {
			off += idx[i] * strides[d]
		}
		dst[outIdx] = combine(dst[outIdx], src[off])
		for i := len(idx) - 1; i >= 0; i-- {
			idx[i]++
			if idx[i] < reduceShape[i] {
				break
			}
			idx[i] = 0
		}
	}
}

func outerOffset(o int, outerDims, shape, strides []int) int {
	off := 0
	for i := len(outerDims) - 1; i >= 0; i-- {
		d := outerDims[i]
		off += (o % shape[d]) * strides[d]
		o /= shape[d]
	}
	return off
}

func outShapeFor(plan Plan) []int { return plan.OutputShape }
func outStridesFor(plan Plan) []int {
	out := make([]int, len(plan.OutputShape))
	acc := 1
	for i := len(out) - 1; i >= 0; i-- {
		out[i] = acc
		if plan.OutputShape[i] > 0 {
			acc *= plan.OutputShape[i]
		}
	}
	return out
}

func reduceAround(t, means *tensor.Tensor, dims []int, keepDims bool,
	combine func(acc, v float64) float64, init float64,
	finalize func(acc, n float64) float64) (*tensor.Tensor, error) {
	plan, err := PlanReduction(t.Shape().Dims(), dims, keepDims)
	if err != nil {
		return nil, err
	}
	out, err := tensor.New(tensor.Float64, plan.OutputShape)
	if err != nil {
		return nil, err
	}
	src := t.Float64()
	m := means.Float64()
	dst := out.Float64()
	for i := range dst {
		dst[i] = init
	}
	strides := plan.InputStrides
	reduceDims := plan.ReduceDims
	reduceShape := make([]int, len(reduceDims))
	for i, d := range reduceDims {
		reduceShape[i] = plan.InputShape[d]
	}
	meanStrides := rowMajorStrides(plan.OutputShape)
	outerDims := plan.OuterDims
	outerNum := 1
	for _, d := range outerDims {
		outerNum *= plan.InputShape[d]
	}
	n := 1
	for _, d := range reduceShape {
		n *= d
	}
	for o := 0; o < outerNum; o++ {
		inBase := outerOffset(o, outerDims, plan.InputShape, strides)
		outIdx := outerOffset(o, outerDims, plan.OutputShape, meanStrides)
		meanIdx := outIdx
		if len(reduceDims) == 0 {
			d := combine(init, src[inBase]-m[meanIdx])
			dst[outIdx] = finalize(d, 1)
			continue
		}
		idx := make([]int, len(reduceDims))
		for k := 0; k < n; k++ {
			off := inBase
			for i, d := range reduceDims {
				off += idx[i] * strides[d]
			}
			dst[outIdx] = combine(dst[outIdx], src[off]-m[meanIdx])
			for i := len(idx) - 1; i >= 0; i-- {
				idx[i]++
				if idx[i] < reduceShape[i] {
					break
				}
				idx[i] = 0
			}
		}
		dst[outIdx] = finalize(dst[outIdx], float64(n))
	}
	return out, nil
}

func argReduce(t *tensor.Tensor, dim int, better func(a, b float64) bool) (*tensor.Tensor, error) {
	if t == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if t.DType() != tensor.Float64 {
		return nil, errors.New(errors.CodeDTypeMismatch, "reductions require float64").
			WithField("dtype", t.DType())
	}
	rank := t.Shape().Rank()
	if dim < 0 || dim >= rank {
		return nil, errors.New(errors.CodeInvalidArgument, "dim out of range").
			WithField("dim", dim).WithField("rank", rank)
	}
	outShape := make([]int, 0, rank-1)
	for i := 0; i < rank; i++ {
		if i != dim {
			outShape = append(outShape, t.Shape().Dim(i))
		}
	}
	out, err := tensor.New(tensor.Int64, outShape)
	if err != nil {
		return nil, err
	}
	src := t.Float64()
	dst := out.Int64()
	strides := t.Strides()
	axisStride := strides[dim]
	axisSize := t.Shape().Dim(dim)
	total := t.Shape().NumElements()
	outer := total / (axisSize * axisStride)
	for o := 0; o < outer; o++ {
		base := o * axisSize * axisStride
		for j := 0; j < axisStride; j++ {
			bestIdx := 0
			bestVal := src[base+j]
			for i := 1; i < axisSize; i++ {
				v := src[base+i*axisStride+j]
				if better(v, bestVal) {
					bestVal = v
					bestIdx = i
				}
			}
			dst[o*axisStride+j] = int64(bestIdx)
		}
	}
	return out, nil
}

func shift(t, maxes *tensor.Tensor, dims []int) (*tensor.Tensor, error) {
	plan, err := PlanReduction(t.Shape().Dims(), dims, true)
	if err != nil {
		return nil, err
	}
	out, err := tensor.New(tensor.Float64, t.Shape().Dims())
	if err != nil {
		return nil, err
	}
	src := t.Float64()
	m := maxes.Float64()
	dst := out.Float64()
	strides := plan.InputStrides
	outerDims := plan.OuterDims
	reduceDims := plan.ReduceDims
	outerNum := 1
	for _, d := range outerDims {
		outerNum *= plan.InputShape[d]
	}
	n := 1
	for _, d := range reduceDims {
		n *= plan.InputShape[d]
	}
	meanStrides := rowMajorStrides(plan.OutputShape)
	for o := 0; o < outerNum; o++ {
		inBase := outerOffset(o, outerDims, plan.InputShape, strides)
		meanIdx := outerOffset(o, outerDims, plan.OutputShape, meanStrides)
		if n == 0 {
			continue
		}
		if len(reduceDims) == 0 {
			dst[inBase] = src[inBase] - m[meanIdx]
			continue
		}
		idx := make([]int, len(reduceDims))
		for k := 0; k < n; k++ {
			off := inBase
			for i, d := range reduceDims {
				off += idx[i] * strides[d]
			}
			dst[off] = src[off] - m[meanIdx]
			for i := len(idx) - 1; i >= 0; i-- {
				idx[i]++
				if idx[i] < plan.InputShape[reduceDims[i]] {
					break
				}
				idx[i] = 0
			}
		}
	}
	return out, nil
}

func squeeze(t *tensor.Tensor) (*tensor.Tensor, error) {
	shape := t.Shape().Dims()
	out := make([]int, 0, len(shape))
	for _, d := range shape {
		if d != 1 {
			out = append(out, d)
		}
	}
	return t.Reshape(out...)
}
