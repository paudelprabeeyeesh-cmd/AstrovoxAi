package math

import (
	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
)

// ConvMode selects the convolution algorithm.
type ConvMode int

// Convolution algorithm selection.
const (
	ConvAuto ConvMode = iota
	ConvDirect
	ConvIm2Col
)

// Conv1d computes a 1-D convolution over input x with kernel k.
// Layout: x = [N, C, L], k = [F, C, K], output = [N, F, L'].
func Conv1d(x, k *tensor.Tensor, stride, padding int, mode ConvMode) (*tensor.Tensor, error) {
	if x == nil || k == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.Shape().Rank() != 3 || k.Shape().Rank() != 3 {
		return nil, errors.New(errors.CodeInvalidArgument, "conv1d requires rank-3 inputs")
	}
	n, c, l := x.Shape().Dim(0), x.Shape().Dim(1), x.Shape().Dim(2)
	f, kc, kw := k.Shape().Dim(0), k.Shape().Dim(1), k.Shape().Dim(2)
	if c != kc {
		return nil, errors.New(errors.CodeShapeMismatch, "conv1d channel mismatch")
	}
	if stride < 1 || padding < 0 {
		return nil, errors.New(errors.CodeInvalidArgument, "conv1d stride/padding invalid")
	}
	outL := (l+2*padding-kw)/stride + 1
	if outL < 1 {
		return nil, errors.New(errors.CodeInvalidArgument, "conv1d output length < 1")
	}
	out, err := tensor.New(tensor.Float64, []int{n, f, outL})
	if err != nil {
		return nil, err
	}
	xv := x.Float64()
	kv := k.Float64()
	ov := out.Float64()
	for ni := 0; ni < n; ni++ {
		for fi := 0; fi < f; fi++ {
			for oi := 0; oi < outL; oi++ {
				var acc float64
				for ci := 0; ci < c; ci++ {
					for ki := 0; ki < kw; ki++ {
						pos := oi*stride + ki - padding
						if pos < 0 || pos >= l {
							continue
						}
						acc += xv[ni*c*l+ci*l+pos] * kv[fi*c*kw+ci*kw+ki]
					}
				}
				ov[ni*f*outL+fi*outL+oi] = acc
			}
		}
	}
	return out, nil
}

// Conv2d computes a 2-D convolution over input x with kernel k.
// Layout: x = [N, C, H, W], k = [F, C, KH, KW], output = [N, F, OH, OW].
// Large kernels select the im2col+GEMM path.
func Conv2d(x, k *tensor.Tensor, strideH, strideW, padH, padW int, mode ConvMode) (*tensor.Tensor, error) {
	if x == nil || k == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.Shape().Rank() != 4 || k.Shape().Rank() != 4 {
		return nil, errors.New(errors.CodeInvalidArgument, "conv2d requires rank-4 inputs")
	}
	n, c, h, w := x.Shape().Dim(0), x.Shape().Dim(1), x.Shape().Dim(2), x.Shape().Dim(3)
	f, kc, kh, kw := k.Shape().Dim(0), k.Shape().Dim(1), k.Shape().Dim(2), k.Shape().Dim(3)
	if c != kc {
		return nil, errors.New(errors.CodeShapeMismatch, "conv2d channel mismatch")
	}
	oh := (h+2*padH-kh)/strideH + 1
	ow := (w+2*padW-kw)/strideW + 1
	if oh < 1 || ow < 1 {
		return nil, errors.New(errors.CodeInvalidArgument, "conv2d output dims < 1")
	}
	out, err := tensor.New(tensor.Float64, []int{n, f, oh, ow})
	if err != nil {
		return nil, err
	}
	if mode == ConvAuto {
		if kh*kw >= 9 {
			mode = ConvIm2Col
		} else {
			mode = ConvDirect
		}
	}
	xv := x.Float64()
	kv := k.Float64()
	ov := out.Float64()
	if mode == ConvIm2Col {
		conv2dIm2Col(xv, kv, ov, n, c, h, w, f, kh, kw, oh, ow, strideH, strideW, padH, padW)
	} else {
		conv2dDirect(xv, kv, ov, n, c, h, w, f, kh, kw, oh, ow, strideH, strideW, padH, padW)
	}
	return out, nil
}

func conv2dDirect(xv, kv, ov []float64, n, c, h, w, f, kh, kw, oh, ow, sh, sw, ph, pw int) {
	for ni := 0; ni < n; ni++ {
		for fi := 0; fi < f; fi++ {
			for oy := 0; oy < oh; oy++ {
				for ox := 0; ox < ow; ox++ {
					var acc float64
					for ci := 0; ci < c; ci++ {
						for ky := 0; ky < kh; ky++ {
							for kx := 0; kx < kw; kx++ {
								iy := oy*sh + ky - ph
								ix := ox*sw + kx - pw
								if iy < 0 || iy >= h || ix < 0 || ix >= w {
									continue
								}
								acc += xv[((ni*c+ci)*h+iy)*w+ix] * kv[((fi*c+ci)*kh+ky)*kw+kx]
							}
						}
					}
					ov[((ni*f+fi)*oh+oy)*ow+ox] = acc
				}
			}
		}
	}
}

// conv2dIm2Col materializes the im2col matrix in blocked form
// and runs the multiply through the blocked GEMM path.
func conv2dIm2Col(xv, kv, ov []float64, n, c, h, w, f, kh, kw, oh, ow, sh, sw, ph, pw int) {
	cols := c * kh * kw
	rows := oh * ow
	// im2col buffer: [rows, cols]
	colBuf := make([]float64, rows*cols)
	// GEMM result buffer: [rows, f]
	tmp := make([]float64, rows*f)
	for ni := 0; ni < n; ni++ {
		for oy := 0; oy < oh; oy++ {
			for ox := 0; ox < ow; ox++ {
				row := oy*ow + ox
				col := 0
				for ci := 0; ci < c; ci++ {
					for ky := 0; ky < kh; ky++ {
						for kx := 0; kx < kw; kx++ {
							iy := oy*sh + ky - ph
							ix := ox*sw + kx - pw
							if iy < 0 || iy >= h || ix < 0 || ix >= w {
								colBuf[row*cols+col] = 0
							} else {
								colBuf[row*cols+col] = xv[((ni*c+ci)*h+iy)*w+ix]
							}
							col++
						}
					}
				}
			}
		}
		// kv is [f, cols]; compute tmp = colBuf * kvᵀ via GEMM.
		gemmBlocked(false, true, 1, colBuf, cols, kv, cols, 0, tmp, rows, f, cols)
		// Transpose [rows, f] into ov layout [f, oh, ow].
		for row := 0; row < rows; row++ {
			oy := row / ow
			ox := row % ow
			for fi := 0; fi < f; fi++ {
				ov[((ni*f+fi)*oh+oy)*ow+ox] = tmp[row*f+fi]
			}
		}
	}
}

// MaxPool2d computes 2-D max pooling over x = [N, C, H, W].
func MaxPool2d(x *tensor.Tensor, kh, kw, strideH, strideW, padH, padW int) (*tensor.Tensor, error) {
	if x == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.Shape().Rank() != 4 {
		return nil, errors.New(errors.CodeInvalidArgument, "maxpool requires rank-4 tensor")
	}
	n, c, h, w := x.Shape().Dim(0), x.Shape().Dim(1), x.Shape().Dim(2), x.Shape().Dim(3)
	oh := (h+2*padH-kh)/strideH + 1
	ow := (w+2*padW-kw)/strideW + 1
	if oh < 1 || ow < 1 {
		return nil, errors.New(errors.CodeInvalidArgument, "maxpool output dims < 1")
	}
	out, err := tensor.New(tensor.Float64, []int{n, c, oh, ow})
	if err != nil {
		return nil, err
	}
	xv := x.Float64()
	ov := out.Float64()
	for ni := 0; ni < n; ni++ {
		for ci := 0; ci < c; ci++ {
			for oy := 0; oy < oh; oy++ {
				for ox := 0; ox < ow; ox++ {
					max := mathInfNeg()
					for ky := 0; ky < kh; ky++ {
						for kx := 0; kx < kw; kx++ {
							iy := oy*strideH + ky - padH
							ix := ox*strideW + kx - padW
							if iy < 0 || iy >= h || ix < 0 || ix >= w {
								continue
							}
							v := xv[((ni*c+ci)*h+iy)*w+ix]
							if v > max {
								max = v
							}
						}
					}
					ov[((ni*c+ci)*oh+oy)*ow+ox] = max
				}
			}
		}
	}
	return out, nil
}

func mathInfNeg() float64 {
	return infNeg
}
