// Package math provides Winograd convolution kernels.
package math

import (
	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
)

// WinogradConv2d computes 2-D convolution using Winograd's
// minimal filtering algorithm F(m x m, r x r).
// For 3x3 kernels, F(2x2, 3x3) requires 4 multiplies per output
// tile vs 9 for direct convolution.
func WinogradConv2d(x, k *tensor.Tensor, strideH, strideW, padH, padW int) (*tensor.Tensor, error) {
	if x == nil || k == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if x.Shape().Rank() != 4 || k.Shape().Rank() != 4 {
		return nil, errors.New(errors.CodeInvalidArgument, "winograd requires rank-4 inputs")
	}
	n, c, h, w := x.Shape().Dim(0), x.Shape().Dim(1), x.Shape().Dim(2), x.Shape().Dim(3)
	f, kc, kh, kw := k.Shape().Dim(0), k.Shape().Dim(1), k.Shape().Dim(2), k.Shape().Dim(3)
	if c != kc {
		return nil, errors.New(errors.CodeShapeMismatch, "winograd channel mismatch")
	}
	if kh != 3 || kw != 3 {
		return nil, errors.New(errors.CodeInvalidArgument, "winograd only supports 3x3 kernels")
	}
	if strideH != 1 || strideW != 1 {
		return nil, errors.New(errors.CodeInvalidArgument, "winograd only supports stride 1")
	}

	// Output dimensions for F(2x2, 3x3): tile size 2, output tile 2x2
	// Input tile: 4x4, Output tile: 2x2
	oh := (h + 2*padH - 2) / 2
	ow := (w + 2*padW - 2) / 2
	if oh < 1 || ow < 1 {
		return nil, errors.New(errors.CodeInvalidArgument, "winograd output dims < 1")
	}
	// Adjust for non-multiple-of-2 output
	oh = (h+2*padH-kh)/strideH + 1
	ow = (w+2*padW-kw)/strideW + 1

	out, err := tensor.New(tensor.Float64, []int{n, f, oh, ow})
	if err != nil {
		return nil, err
	}

	xv := x.Float64()
	kv := k.Float64()
	ov := out.Float64()

	// Transform kernel: G * K * G^T
	// G (4x3) for F(2x2, 3x3)
	G := []float64{
		1, 0, 0,
		0.5, 0.5, 0.5,
		0.5, -0.5, 0.5,
		0, 0, 1,
	}
	// G^T (3x4)
	GT := []float64{
		1, 0.5, 0.5, 0,
		0, 0.5, -0.5, 0,
		0, 0.5, 0.5, 1,
	}

	// Transform kernel weights: U = G * K * G^T for each filter/channel
	// K is [f, c, 3, 3], U will be [f, c, 4, 4]
	U := make([]float64, f*c*4*4)
	for fi := 0; fi < f; fi++ {
		for ci := 0; ci < c; ci++ {
			K := kv[((fi*c+ci)*3)*3 : ((fi*c+ci)*3+3)*3]
			// U = G * K * G^T
			UK := matMul3x4x3(G, K, 4, 3, 3)
			U_fi_ci := matMul4x3x4(UK, GT, 4, 3, 4)
			copy(U[(fi*c+ci)*16:(fi*c+ci+1)*16], U_fi_ci)
		}
	}

	// Process each sample
	for ni := 0; ni < n; ni++ {
		// Tile the input into 4x4 patches
		// Output tiles are 2x2
		tileH := (h+2*padH-3)/2 + 1
		tileW := (w+2*padW-3)/2 + 1

		// Winograd transform matrices for input
		// B^T * d * B where B is 4x4
		B := []float64{
			1, 0, -1, 0,
			0, 1, 1, 0,
			0, -1, 1, 0,
			0, 1, 0, -1,
		}
		BT := []float64{
			1, 0, 0, 0,
			0, 1, -1, 1,
			-1, 1, 1, 0,
			0, 0, 0, -1,
		}

		for ti := 0; ti < tileH; ti++ {
			for tj := 0; tj < tileW; tj++ {
				// Extract 4x4 input patch for each channel
				V := make([]float64, c*4*4)
				for ci := 0; ci < c; ci++ {
					patch := extractPatch4x4(xv, ni, ci, c, h, w, ti, tj, padH, padW)
					// V = B^T * patch * B
					BT_patch := matMul4x4x4(BT, patch, 4, 4, 4)
					V_ci := matMul4x4x4(BT_patch, B, 4, 4, 4)
					copy(V[ci*16:(ci+1)*16], V_ci)
				}

				// Element-wise multiply and accumulate over channels
				// M = U * V (element-wise) summed over channels
				M := make([]float64, f*4*4)
				for fi := 0; fi < f; fi++ {
					for i := 0; i < 16; i++ {
						var sum float64
						for ci := 0; ci < c; ci++ {
							sum += U[(fi*c+ci)*16+i] * V[ci*16+i]
						}
						M[fi*16+i] = sum
					}
				}

				// Inverse transform: A^T * M * A
				// A^T (2x4), A (4x2)
				AT := []float64{
					1, 1, 1, 0,
					0, 1, -1, -1,
				}
				A := []float64{
					1, 0,
					1, 1,
					1, -1,
					0, -1,
				}

				for fi := 0; fi < f; fi++ {
					AT_M := matMul2x4x4(AT, M[fi*16:], 2, 4, 4)
					Y := matMul2x4x2(AT_M, A, 2, 4, 2)
					// Write 2x2 output tile
					oy := ti * 2
					ox := tj * 2
					for dy := 0; dy < 2; dy++ {
						for dx := 0; dx < 2; dx++ {
							outY := oy + dy
							outX := ox + dx
							if outY < oh && outX < ow {
								ov[((ni*f+fi)*oh+outY)*ow+outX] = Y[dy*2+dx]
							}
						}
					}
				}
			}
		}
	}

	return out, nil
}

// Helper functions for small matrix multiplications.

func matMul3x4x3(A, B []float64, m, k, n int) []float64 {
	C := make([]float64, m*n)
	for i := 0; i < m; i++ {
		for j := 0; j < n; j++ {
			var sum float64
			for p := 0; p < k; p++ {
				sum += A[i*k+p] * B[p*n+j]
			}
			C[i*n+j] = sum
		}
	}
	return C
}

func matMul4x3x4(A, B []float64, m, k, n int) []float64 {
	C := make([]float64, m*n)
	for i := 0; i < m; i++ {
		for j := 0; j < n; j++ {
			var sum float64
			for p := 0; p < k; p++ {
				sum += A[i*k+p] * B[p*n+j]
			}
			C[i*n+j] = sum
		}
	}
	return C
}

func matMul4x4x4(A, B []float64, m, k, n int) []float64 {
	C := make([]float64, m*n)
	for i := 0; i < m; i++ {
		for j := 0; j < n; j++ {
			var sum float64
			for p := 0; p < k; p++ {
				sum += A[i*k+p] * B[p*n+j]
			}
			C[i*n+j] = sum
		}
	}
	return C
}

func matMul2x4x4(A, B []float64, m, k, n int) []float64 {
	C := make([]float64, m*n)
	for i := 0; i < m; i++ {
		for j := 0; j < n; j++ {
			var sum float64
			for p := 0; p < k; p++ {
				sum += A[i*k+p] * B[p*n+j]
			}
			C[i*n+j] = sum
		}
	}
	return C
}

func matMul2x4x2(A, B []float64, m, k, n int) []float64 {
	C := make([]float64, m*n)
	for i := 0; i < m; i++ {
		for j := 0; j < n; j++ {
			var sum float64
			for p := 0; p < k; p++ {
				sum += A[i*k+p] * B[p*n+j]
			}
			C[i*n+j] = sum
		}
	}
	return C
}

func extractPatch4x4(xv []float64, ni, ci, c, h, w, ti, tj, padH, padW int) []float64 {
	patch := make([]float64, 16)
	for py := 0; py < 4; py++ {
		for px := 0; px < 4; px++ {
			iy := ti*2 + py - padH
			ix := tj*2 + px - padW
			if iy >= 0 && iy < h && ix >= 0 && ix < w {
				patch[py*4+px] = xv[((ni*c+ci)*h+iy)*w+ix]
			} else {
				patch[py*4+px] = 0
			}
		}
	}
	return patch
}
