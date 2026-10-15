package math

import (
	"math"
	"testing"

	"github.com/astrovox/astrovox/tensor"
)

// This suite is the first verification of the tensor/math library, which is
// used by production inference paths (internal/ai, internal/distributed) but
// had no test files. Every kernel is checked against an independent,
// deliberately naive reference implementation, and every analytic backward
// is checked against central finite differences. Reference implementations
// are the correctness oracles; kernels must agree with them.

// --- helpers ---------------------------------------------------------------

// newF64 builds a contiguous float64 tensor and fills it with vals.
func newF64(vals []float64, dims ...int) *tensor.Tensor {
	t, err := tensor.New(tensor.Float64, dims)
	if err != nil {
		panic(err)
	}
	copy(t.Float64(), vals)
	return t
}

// flat returns the tensor's flat float64 data.
func flat(t *tensor.Tensor) []float64 { return t.Float64() }

// near reports whether two float64 slices agree within tol elementwise.
func near(t *testing.T, name string, got, want []float64, tol float64) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("%s: length %d, want %d", name, len(got), len(want))
	}
	for i := range got {
		if math.IsNaN(got[i]) || math.Abs(got[i]-want[i]) > tol {
			t.Fatalf("%s: element %d = %v, want %v (tol %g)", name, i, got[i], want[i], tol)
		}
	}
}

// numericGrad central-differences the loss along every element of x.
func numericGrad(loss func(x *tensor.Tensor) float64, x *tensor.Tensor) []float64 {
	xv := x.Float64()
	n := len(xv)
	g := make([]float64, n)
	const h = 1e-6
	for i := 0; i < n; i++ {
		orig := xv[i]
		xv[i] = orig + h
		fp := loss(x)
		xv[i] = orig - h
		fm := loss(x)
		xv[i] = orig
		g[i] = (fp - fm) / (2 * h)
	}
	return g
}

// seq fills dims with deterministic pseudo-random-ish values.
func seq(dims ...int) []float64 {
	n := 1
	for _, d := range dims {
		n *= d
	}
	out := make([]float64, n)
	for i := range out {
		out[i] = math.Sin(float64(i+1)) * 0.7
	}
	return out
}

// --- reference implementations ----------------------------------------------

// refMatMul is the textbook triple loop: O(m*n*k), no blocking.
func refMatMul(a, b []float64, m, k, n int) []float64 {
	out := make([]float64, m*n)
	for i := 0; i < m; i++ {
		for j := 0; j < n; j++ {
			var acc float64
			for p := 0; p < k; p++ {
				acc += a[i*k+p] * b[p*n+j]
			}
			out[i*n+j] = acc
		}
	}
	return out
}

func refConv2d(x, k []float64, n, c, h, w, f, kh, kw, oh, ow, sh, sw, ph, pw int) []float64 {
	out := make([]float64, n*f*oh*ow)
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
								acc += x[((ni*c+ci)*h+iy)*w+ix] * k[((fi*c+ci)*kh+ky)*kw+kx]
							}
						}
					}
					out[((ni*f+fi)*oh+oy)*ow+ox] = acc
				}
			}
		}
	}
	return out
}

// --- GEMM -------------------------------------------------------------------

func TestGEMMAllTransposeCombos(t *testing.T) {
	cases := []struct{ m, n, k int }{
		{3, 4, 5},       // small
		{130, 140, 150}, // crosses the 96/256 cache blocks
	}
	for _, transA := range []bool{false, true} {
		for _, transB := range []bool{false, true} {
			for _, cs := range cases {
				m, n, k := cs.m, cs.n, cs.k
				var aVals, bVals []float64
				if transA {
					aVals = seq(k, m) // stored [k, m]
				} else {
					aVals = seq(m, k) // stored [m, k]
				}
				if transB {
					bVals = seq(n, k) // stored [n, k]
				} else {
					bVals = seq(k, n) // stored [k, n]
				}
				aShape := []int{k, m}
				if !transA {
					aShape = []int{m, k}
				}
				bShape := []int{n, k}
				if !transB {
					bShape = []int{k, n}
				}
				A := newF64(aVals, aShape...)
				B := newF64(bVals, bShape...)
				// Pre-fill C so beta accumulation is exercised.
				cVals := seq(m, n)
				for i := range cVals {
					cVals[i] *= 0.1
				}
				C := newF64(cVals, m, n)

				const alpha, beta = 2.0, 0.5
				if err := GEMM(transA, transB, alpha, A, B, beta, C); err != nil {
					t.Fatalf("GEMM(transA=%v,transB=%v,%dx%dx%d): %v", transA, transB, m, n, k, err)
				}

				// Reference: op(A) is [m,k], op(B) is [k,n].
				opA := make([]float64, m*k)
				for i := 0; i < m; i++ {
					for p := 0; p < k; p++ {
						if transA {
							opA[i*k+p] = aVals[p*m+i]
						} else {
							opA[i*k+p] = aVals[i*k+p]
						}
					}
				}
				opB := make([]float64, k*n)
				for p := 0; p < k; p++ {
					for j := 0; j < n; j++ {
						if transB {
							opB[p*n+j] = bVals[j*k+p]
						} else {
							opB[p*n+j] = bVals[p*n+j]
						}
					}
				}
				want := refMatMul(opA, opB, m, k, n)
				for i := range want {
					want[i] = alpha*want[i] + beta*cVals[i]
				}
				near(t, "GEMM", flat(C), want, 1e-9)
			}
		}
	}
}

func TestGEMMErrors(t *testing.T) {
	A := newF64(seq(2, 3), 2, 3)
	B := newF64(seq(3, 2), 3, 2)
	C := newF64(make([]float64, 4), 2, 2)
	if err := GEMM(false, false, 1, A, B, 0, C); err != nil {
		t.Fatalf("valid GEMM: %v", err)
	}
	// Contracting-dim mismatch.
	bad := newF64(seq(4, 2), 4, 2)
	if err := GEMM(false, false, 1, A, bad, 0, C); err == nil {
		t.Fatal("a contracting-dim mismatch was accepted")
	}
	// Output shape mismatch.
	small := newF64(make([]float64, 1), 1, 1)
	if err := GEMM(false, false, 1, A, B, 0, small); err == nil {
		t.Fatal("an output shape mismatch was accepted")
	}
	// Non-contiguous input.
	T, err := newF64(seq(3, 2), 3, 2).Transpose(0, 1)
	if err != nil {
		t.Fatalf("Transpose: %v", err)
	}
	if err := GEMM(false, false, 1, T, B, 0, C); err == nil {
		t.Fatal("a non-contiguous input was accepted")
	}
	if err := GEMM(false, false, 1, nil, B, 0, C); err == nil {
		t.Fatal("a nil input was accepted")
	}
}

func TestMatMulMatVecBatch(t *testing.T) {
	a := seq(3, 4)
	b := seq(4, 5)
	out, err := MatMul(newF64(a, 3, 4), newF64(b, 4, 5))
	if err != nil {
		t.Fatalf("MatMul: %v", err)
	}
	near(t, "MatMul", flat(out), refMatMul(a, b, 3, 4, 5), 1e-9)

	x := seq(4)
	v, err := MatVec(newF64(a, 3, 4), newF64(x, 4))
	if err != nil {
		t.Fatalf("MatVec: %v", err)
	}
	rmv := refMatMul(a, x, 3, 4, 1)
	near(t, "MatVec", flat(v), rmv, 1e-9)

	// Batched: two independent 2x3 @ 3x2 products.
	ba := make([]float64, 12)
	bb := make([]float64, 12)
	for i := range ba {
		ba[i] = float64(i%5) - 2.0
		bb[i] = float64((i+1)%4) * 0.5
	}
	bm, err := BatchMatMul(newF64(ba, 2, 2, 3), newF64(bb, 2, 3, 2))
	if err != nil {
		t.Fatalf("BatchMatMul: %v", err)
	}
	want := append(refMatMul(ba[:6], bb[:6], 2, 3, 2), refMatMul(ba[6:], bb[6:], 2, 3, 2)...)
	near(t, "BatchMatMul", flat(bm), want, 1e-9)
}

// --- convolution -------------------------------------------------------------

func TestConv2dDirectVsIm2ColVsReference(t *testing.T) {
	n, c, h, w := 2, 3, 8, 9
	f, kh, kw := 4, 3, 3
	x := newF64(seq(n, c, h, w), n, c, h, w)
	k := newF64(seq(f, c, kh, kw), f, c, kh, kw)

	direct, err := Conv2d(x, k, 1, 1, 1, 1, ConvDirect)
	if err != nil {
		t.Fatalf("ConvDirect: %v", err)
	}
	im2col, err := Conv2d(x, k, 1, 1, 1, 1, ConvIm2Col)
	if err != nil {
		t.Fatalf("ConvIm2Col: %v", err)
	}
	oh := (h + 2 - kh) + 1
	ow := (w + 2 - kw) + 1
	want := refConv2d(flat(x), flat(k), n, c, h, w, f, kh, kw, oh, ow, 1, 1, 1, 1)
	near(t, "Conv2dDirect", flat(direct), want, 1e-9)
	near(t, "Conv2dIm2Col", flat(im2col), want, 1e-9)

	// Auto-selection (3x3 kernel -> im2col path) must agree too.
	auto, err := Conv2d(x, k, 1, 1, 1, 1, ConvAuto)
	if err != nil {
		t.Fatalf("ConvAuto: %v", err)
	}
	near(t, "Conv2dAuto", flat(auto), want, 1e-9)

	// A strided case against the reference.
	sh, sw, ph, pw := 2, 2, 0, 0
	oh = (h-kh)/sh + 1
	ow = (w-kw)/sw + 1
	str, err := Conv2d(x, k, sh, sw, ph, pw, ConvDirect)
	if err != nil {
		t.Fatalf("Conv2d stride: %v", err)
	}
	wantS := refConv2d(flat(x), flat(k), n, c, h, w, f, kh, kw, oh, ow, sh, sw, ph, pw)
	near(t, "Conv2dStride", flat(str), wantS, 1e-9)
}

func TestConv1dVsReference(t *testing.T) {
	n, c, l := 2, 3, 7
	f, kw := 4, 3
	x := newF64(seq(n, c, l), n, c, l)
	k := newF64(seq(f, c, kw), f, c, kw)
	out, err := Conv1d(x, k, 1, 1, ConvDirect)
	if err != nil {
		t.Fatalf("Conv1d: %v", err)
	}
	outL := (l + 2 - kw) + 1
	xv, kv, ov := flat(x), flat(k), flat(out)
	for ni := 0; ni < n; ni++ {
		for fi := 0; fi < f; fi++ {
			for oi := 0; oi < outL; oi++ {
				var acc float64
				for ci := 0; ci < c; ci++ {
					for ki := 0; ki < kw; ki++ {
						pos := oi + ki - 1
						if pos < 0 || pos >= l {
							continue
						}
						acc += xv[ni*c*l+ci*l+pos] * kv[fi*c*kw+ci*kw+ki]
					}
				}
				if got := ov[ni*f*outL+fi*outL+oi]; math.Abs(got-acc) > 1e-9 {
					t.Fatalf("Conv1d[%d,%d,%d] = %v, want %v", ni, fi, oi, got, acc)
				}
			}
		}
	}
}

func TestMaxPool2dVsReference(t *testing.T) {
	n, c, h, w := 1, 2, 4, 5
	x := newF64(seq(n, c, h, w), n, c, h, w)
	kh, kw, sh, sw := 2, 2, 2, 2
	out, err := MaxPool2d(x, kh, kw, sh, sw, 0, 0)
	if err != nil {
		t.Fatalf("MaxPool2d: %v", err)
	}
	oh := (h-kh)/sh + 1
	ow := (w-kw)/sw + 1
	xv, ov := flat(x), flat(out)
	for ni := 0; ni < n; ni++ {
		for ci := 0; ci < c; ci++ {
			for oy := 0; oy < oh; oy++ {
				for ox := 0; ox < ow; ox++ {
					best := math.Inf(-1)
					for ky := 0; ky < kh; ky++ {
						for kx := 0; kx < kw; kx++ {
							v := xv[((ni*c+ci)*h+oy*sh+ky)*w+ox*sw+kx]
							if v > best {
								best = v
							}
						}
					}
					if got := ov[((ni*c+ci)*oh+oy)*ow+ox]; got != best {
						t.Fatalf("MaxPool2d[%d,%d,%d,%d] = %v, want %v", ni, ci, oy, ox, got, best)
					}
				}
			}
		}
	}
}

// --- normalization -----------------------------------------------------------

func refLayerNorm(x []float64, w, b []float64, eps float64) []float64 {
	d := len(x)
	out := make([]float64, d)
	var mean float64
	for _, v := range x {
		mean += v
	}
	mean /= float64(d)
	var vs float64
	for _, v := range x {
		vs += (v - mean) * (v - mean)
	}
	inv := 1 / math.Sqrt(vs/float64(d)+eps)
	for i, v := range x {
		n := (v - mean) * inv
		if w != nil {
			n *= w[i]
		}
		if b != nil {
			n += b[i]
		}
		out[i] = n
	}
	return out
}

func TestLayerNormForward(t *testing.T) {
	rows := [][]float64{{1, 2, 3, 4}, {-5, 0, 5, 10}, {100, 100, 100, 100}}
	w := []float64{1.5, -0.5, 2, 0.25}
	b := []float64{0.1, 0.2, 0.3, 0.4}
	var all []float64
	var wantAll []float64
	for _, r := range rows {
		all = append(all, r...)
		wantAll = append(wantAll, refLayerNorm(r, w, b, 1e-5)...)
	}
	x := newF64(all, len(rows), 4)
	out, err := LayerNorm(x, newF64(w, 4), newF64(b, 4), 1e-5)
	if err != nil {
		t.Fatalf("LayerNorm: %v", err)
	}
	near(t, "LayerNorm", flat(out), wantAll, 1e-9)
}

// TestLayerNormBackwardFiniteDifferences is the regression test for the
// adjoint formula: the old code accumulated dy*x instead of dy*xHat, which
// is only correct when the row mean is zero.
func TestLayerNormBackwardFiniteDifferences(t *testing.T) {
	eps := 1e-5
	xVals := []float64{1, 2, 3, 4, -2, -4, 6, 8}
	w := []float64{1.5, -0.5, 2, 0.25}
	b := []float64{0.1, 0.2, 0.3, 0.4}
	gradOut := []float64{0.3, -1, 2, 0.5, 1, 1, -0.5, 0.25}

	// loss(x) = <gradOut, LayerNorm(x, w, b)>: the standard vJp reduction,
	// whose gradient wrt x is exactly what LayerNormBackward computes.
	lossX := func(x *tensor.Tensor) float64 {
		out, err := LayerNorm(x, newF64(w, 4), newF64(b, 4), eps)
		if err != nil {
			t.Fatalf("LayerNorm in loss: %v", err)
		}
		goV, ov := gradOut, flat(out)
		var s float64
		for i := range goV {
			s += goV[i] * ov[i]
		}
		return s
	}
	lossW := func(wt *tensor.Tensor) float64 {
		out, err := LayerNorm(newF64(xVals, 2, 4), wt, newF64(b, 4), eps)
		if err != nil {
			t.Fatalf("LayerNorm in loss: %v", err)
		}
		goV, ov := gradOut, flat(out)
		var s float64
		for i := range goV {
			s += goV[i] * ov[i]
		}
		return s
	}
	lossB := func(bt *tensor.Tensor) float64 {
		out, err := LayerNorm(newF64(xVals, 2, 4), newF64(w, 4), bt, eps)
		if err != nil {
			t.Fatalf("LayerNorm in loss: %v", err)
		}
		goV, ov := gradOut, flat(out)
		var s float64
		for i := range goV {
			s += goV[i] * ov[i]
		}
		return s
	}

	dx, dw, db, err := LayerNormBackward(
		newF64(gradOut, 2, 4), newF64(xVals, 2, 4),
		newF64(w, 4), newF64(b, 4), eps)
	if err != nil {
		t.Fatalf("LayerNormBackward: %v", err)
	}
	near(t, "dx", flat(dx), numericGrad(lossX, newF64(xVals, 2, 4)), 1e-4)
	near(t, "dw", flat(dw), numericGrad(lossW, newF64(w, 4)), 1e-4)
	near(t, "db", flat(db), numericGrad(lossB, newF64(b, 4)), 1e-4)
}

func TestGroupNormForward(t *testing.T) {
	// [N=2, C=4, H=2, W=2] with 2 groups.
	n, c, h, w := 2, 4, 2, 2
	x := newF64(seq(n, c, h, w), n, c, h, w)
	w8 := []float64{1, 2, 0.5, 1.5}
	b8 := []float64{0, 1, -1, 0.5}
	out, err := GroupNorm(x, newF64(w8, 4), newF64(b8, 4), 2, 1e-5)
	if err != nil {
		t.Fatalf("GroupNorm: %v", err)
	}
	// Reference: normalize over each (n, group) block of 2 channels.
	xv, ov := flat(x), flat(out)
	channelsPerGroup := c / 2
	spatial := h * w
	groupSize := channelsPerGroup * spatial
	for ni := 0; ni < n; ni++ {
		for g := 0; g < 2; g++ {
			var sum float64
			for ci := 0; ci < channelsPerGroup; ci++ {
				idx := g*channelsPerGroup + ci
				base := (ni*c + idx) * spatial
				for s := 0; s < spatial; s++ {
					sum += xv[base+s]
				}
			}
			mean := sum / float64(groupSize)
			var vs float64
			for ci := 0; ci < channelsPerGroup; ci++ {
				idx := g*channelsPerGroup + ci
				base := (ni*c + idx) * spatial
				for s := 0; s < spatial; s++ {
					d := xv[base+s] - mean
					vs += d * d
				}
			}
			inv := 1 / math.Sqrt(vs/float64(groupSize)+1e-5)
			for ci := 0; ci < channelsPerGroup; ci++ {
				idx := g*channelsPerGroup + ci
				base := (ni*c + idx) * spatial
				for s := 0; s < spatial; s++ {
					want := (xv[base+s]-mean)*inv*w8[idx] + b8[idx]
					if got := ov[base+s]; math.Abs(got-want) > 1e-9 {
						t.Fatalf("GroupNorm mismatch at %d: %v vs %v", base+s, got, want)
					}
				}
			}
		}
	}
}

// TestGroupNormBackwardFiniteDifferences mirrors the layernorm adjoint
// check; GroupNormBackward had the same raw-x adjoint defect.
func TestGroupNormBackwardFiniteDifferences(t *testing.T) {
	eps := 1e-5
	xVals := seq(2, 4, 2, 2)
	w8 := []float64{1, 2, 0.5, 1.5}
	b8 := []float64{0, 1, -1, 0.5}
	gradOut := seq(2, 4, 2, 2)

	dot := func(out []float64) float64 {
		var s float64
		for i := range out {
			s += gradOut[i] * out[i]
		}
		return s
	}
	lossX := func(x *tensor.Tensor) float64 {
		out, err := GroupNorm(x, newF64(w8, 4), newF64(b8, 4), 2, eps)
		if err != nil {
			t.Fatalf("GroupNorm: %v", err)
		}
		return dot(flat(out))
	}
	lossW := func(wt *tensor.Tensor) float64 {
		out, err := GroupNorm(newF64(xVals, 2, 4, 2, 2), wt, newF64(b8, 4), 2, eps)
		if err != nil {
			t.Fatalf("GroupNorm: %v", err)
		}
		return dot(flat(out))
	}
	lossB := func(bt *tensor.Tensor) float64 {
		out, err := GroupNorm(newF64(xVals, 2, 4, 2, 2), newF64(w8, 4), bt, 2, eps)
		if err != nil {
			t.Fatalf("GroupNorm: %v", err)
		}
		return dot(flat(out))
	}

	dx, dw, db, err := GroupNormBackward(
		newF64(gradOut, 2, 4, 2, 2), newF64(xVals, 2, 4, 2, 2),
		newF64(w8, 4), newF64(b8, 4), 2, eps)
	if err != nil {
		t.Fatalf("GroupNormBackward: %v", err)
	}
	near(t, "gdx", flat(dx), numericGrad(lossX, newF64(xVals, 2, 4, 2, 2)), 1e-4)
	near(t, "gdw", flat(dw), numericGrad(lossW, newF64(w8, 4)), 1e-4)
	near(t, "gdb", flat(db), numericGrad(lossB, newF64(b8, 4)), 1e-4)
}

func TestRMSNorm(t *testing.T) {
	x := newF64([]float64{1, 2, 3, 4}, 1, 4)
	w := newF64([]float64{2, 2, 2, 2}, 4)
	b := newF64([]float64{1, 1, 1, 1}, 4)
	out, err := RMSNorm(x, w, b, 1e-5)
	if err != nil {
		t.Fatalf("RMSNorm: %v", err)
	}
	xv := flat(x)
	var sumSq float64
	for _, v := range xv {
		sumSq += v * v
	}
	inv := 1 / math.Sqrt(sumSq/4+1e-5)
	want := make([]float64, 4)
	for i, v := range xv {
		want[i] = v*inv*2 + 1
	}
	near(t, "RMSNorm", flat(out), want, 1e-9)
}

// --- FFT / DCT ----------------------------------------------------------------

func TestFFTVsDFT(t *testing.T) {
	n := 16
	vals := seq(n)
	x := newF64(vals, n)
	// The kernel is float64-typed but returns complex output.
	spec, err := FFT(x, false)
	if err != nil {
		t.Fatalf("FFT: %v", err)
	}
	got := spec.Complex128()
	// Naive DFT as the oracle.
	for k := 0; k < n; k++ {
		var want complex128
		for j := 0; j < n; j++ {
			ang := -2 * math.Pi * float64(k) * float64(j) / float64(n)
			want += complex(vals[j], 0) * complex(math.Cos(ang), math.Sin(ang))
		}
		if math.Abs(real(got[k])-real(want)) > 1e-9 || math.Abs(imag(got[k])-imag(want)) > 1e-9 {
			t.Fatalf("FFT[%d] = %v, want %v", k, got[k], want)
		}
	}
	// Inverse must round-trip: the public wrapper only accepts float64
	// input, so exercise the kernel's inverse path on the spectrum
	// directly (the wrapper refuses a complex input, tested below).
	work := make([]complex128, n)
	for i, v := range vals {
		work[i] = complex(v, 0)
	}
	fft(work, false)
	fft(work, true)
	for i := range work {
		if math.Abs(real(work[i])-vals[i]) > 1e-9 || math.Abs(imag(work[i])) > 1e-9 {
			t.Fatalf("FFT inverse round-trip[%d] = %v, want %v", i, work[i], vals[i])
		}
	}
	// A complex input is refused rather than panicking on the nil view.
	specC, err := FFT(x, false)
	if err != nil {
		t.Fatalf("FFT forward: %v", err)
	}
	if _, err := FFT(specC, true); err == nil {
		t.Fatal("FFT accepted a complex128 input (would panic on the nil float64 view)")
	}
}

// --- fused activations ---------------------------------------------------------

func refAct(v float64, act ActivationType, leak float64) float64 {
	switch act {
	case ActReLU:
		if v < 0 {
			return 0
		}
		return v
	case ActGELU:
		return v * 0.5 * (1 + math.Erf(v/math.Sqrt2))
	case ActSiLU, ActSwish:
		return v / (1 + math.Exp(-v))
	case ActMish:
		return v * math.Tanh(math.Log1p(math.Exp(v)))
	case ActTanh:
		return math.Tanh(v)
	case ActSigmoid:
		return 1 / (1 + math.Exp(-v))
	case ActHardSwish:
		h := math.Min(math.Max(v+3, 0), 6)
		return v * h / 6
	case ActHardSigmoid:
		h := math.Min(math.Max(v+3, 0), 6)
		return h / 6
	case ActELU:
		if v < 0 {
			return math.Exp(v) - 1
		}
		return v
	case ActLeakyReLU:
		if v < 0 {
			return leak * v
		}
		return v
	case ActReLU6:
		return math.Min(math.Max(v, 0), 6)
	}
	return v
}

func TestFusedActApplyAllTypes(t *testing.T) {
	acts := []ActivationType{ActReLU, ActGELU, ActSiLU, ActSwish, ActMish, ActTanh,
		ActSigmoid, ActHardSwish, ActHardSigmoid, ActELU, ActLeakyReLU, ActReLU6}
	in := []float64{-3, -1, -0.5, 0, 0.5, 1, 3, 7}
	const leak = 0.2 // non-default slope: would catch a hardcoded 0.01
	for _, act := range acts {
		x := newF64(append([]float64(nil), in...), len(in))
		if err := FusedActApplyFull(x, act, 1, 0, leak); err != nil {
			t.Fatalf("act %d: %v", act, err)
		}
		want := make([]float64, len(in))
		for i, v := range in {
			want[i] = refAct(v, act, leak)
		}
		near(t, "FusedActApply", flat(x), want, 1e-9)
	}
	// The default slope is 0.01 through the wrapper.
	x := newF64([]float64{-1, 1}, 2)
	if err := FusedActApply(x, ActLeakyReLU, 1, 0); err != nil {
		t.Fatalf("default leaky: %v", err)
	}
	near(t, "default leak slope", flat(x), []float64{-0.01, 1}, 1e-12)

	// An unknown activation is an error, not a pass-through.
	x2 := newF64([]float64{1}, 1)
	if err := FusedActApply(x2, ActivationType(99), 1, 0); err == nil {
		t.Fatal("an unknown activation passed through")
	}
}

func TestFusedLinearAct(t *testing.T) {
	m, k, n := 5, 4, 3
	x := seq(m, k)
	w := seq(n, k) // [N, K] layout: y = x @ W^T + b
	b := []float64{0.1, -0.2, 0.3}
	out := newF64(make([]float64, m*n), m, n)
	if err := FusedLinearAct(newF64(x, m, k), newF64(w, n, k), newF64(b, n), out, ActReLU); err != nil {
		t.Fatalf("FusedLinearAct: %v", err)
	}
	// Reference: relu(x @ W^T + b).
	want := make([]float64, m*n)
	for i := 0; i < m; i++ {
		for j := 0; j < n; j++ {
			var acc float64
			for p := 0; p < k; p++ {
				acc += x[i*k+p] * w[j*k+p]
			}
			acc += b[j]
			if acc < 0 {
				acc = 0
			}
			want[i*n+j] = acc
		}
	}
	near(t, "FusedLinearAct", flat(out), want, 1e-9)

	// An unsupported activation must be reported, not silently skipped.
	out2 := newF64(make([]float64, m*n), m, n)
	if err := FusedLinearAct(newF64(x, m, k), newF64(w, n, k), nil, out2, ActMish); err == nil {
		t.Fatal("an unsupported fused activation was silently skipped")
	}
}

// TestFusedConvActWritesConvolution is the regression test for
// FusedConvAct discarding the Conv2d result: out must receive conv+bias+act.
func TestFusedConvActWritesConvolution(t *testing.T) {
	n, c, h, w := 1, 2, 6, 6
	f, kh, kw := 2, 3, 3
	x := newF64(seq(n, c, h, w), n, c, h, w)
	k := newF64(seq(f, c, kh, kw), f, c, kh, kw)
	b := newF64([]float64{0.5, -0.5}, f)
	oh := (h - kh) + 1
	ow := (w - kw) + 1
	out := newF64(make([]float64, n*f*oh*ow), n, f, oh, ow)

	if err := FusedConvAct(x, k, b, out, 1, 1, 0, 0, ActReLU); err != nil {
		t.Fatalf("FusedConvAct: %v", err)
	}
	conv, err := Conv2d(x, k, 1, 1, 0, 0, ConvDirect)
	if err != nil {
		t.Fatalf("Conv2d: %v", err)
	}
	cv := flat(conv)
	bv := flat(b)
	want := make([]float64, len(cv))
	for i := range cv {
		v := cv[i]
		if i < len(cv) {
			channel := i / (oh * ow)
			v += bv[channel]
		}
		if v < 0 {
			v = 0
		}
		want[i] = v
	}
	near(t, "FusedConvAct", flat(out), want, 1e-9)

	// A wrong out shape is an error, not a silently partial result.
	bad := newF64(make([]float64, 4), 1, 1, 2, 2)
	if err := FusedConvAct(x, k, b, bad, 1, 1, 0, 0, ActReLU); err == nil {
		t.Fatal("a mismatched out shape was accepted")
	}
}

func TestFusedAddAct(t *testing.T) {
	x := newF64([]float64{-2, -1, 0, 1, 2}, 5)
	y := newF64([]float64{-1, 0, 1, 2, 3}, 5)
	out, err := FusedAddAct(x, y, ActReLU)
	if err != nil {
		t.Fatalf("FusedAddAct: %v", err)
	}
	near(t, "FusedAddAct", flat(out), []float64{0, 0, 1, 3, 5}, 1e-12)
}

// --- BLAS -----------------------------------------------------------------------

func TestBlasPrimitives(t *testing.T) {
	x := newF64([]float64{1, 2, 3}, 3)
	y := newF64([]float64{4, 5, 6}, 3)
	if err := Axpy(2, x, y); err != nil {
		t.Fatalf("Axpy: %v", err)
	}
	near(t, "Axpy", flat(y), []float64{6, 9, 12}, 1e-12)

	x2 := newF64([]float64{1, 2, 3}, 3)
	y2 := newF64([]float64{4, 5, 6}, 3)
	d, err := Dot(x2, y2)
	if err != nil {
		t.Fatalf("Dot: %v", err)
	}
	if d != 32 {
		t.Fatalf("Dot = %v, want 32", d)
	}
	nrm, err := Nrm2(newF64([]float64{3, 4}, 2))
	if err != nil {
		t.Fatalf("Nrm2: %v", err)
	}
	if nrm != 5 {
		t.Fatalf("Nrm2 = %v, want 5", nrm)
	}

	// Gemv: y = alpha*A*x + beta*y
	a := newF64(seq(2, 3), 2, 3)
	xx := newF64([]float64{1, -1, 2}, 3)
	yy := newF64([]float64{1, 1}, 2)
	if err := Gemv(false, 2, a, xx, yy, 0.5); err != nil {
		t.Fatalf("Gemv: %v", err)
	}
	av := flat(a)
	want := []float64{
		0.5 + 2*(av[0]-av[1]+2*av[2]),
		0.5 + 2*(av[3]-av[4]+2*av[5]),
	}
	near(t, "Gemv", flat(yy), want, 1e-9)
}

// --- quantization -----------------------------------------------------------------

func TestQuantizeInt8RoundTrip(t *testing.T) {
	vals := []float64{-128, -1, 0, 0.5, 1, 42, 100, 127}
	x := newF64(vals, len(vals))
	q, err := QuantizeInt8(x, &QParams{})
	if err != nil {
		t.Fatalf("QuantizeInt8: %v", err)
	}
	dq, err := DequantizeInt8(q, &QParams{Scale: 127.0 / 127.0})
	if err != nil {
		t.Fatalf("DequantizeInt8: %v", err)
	}
	// Symmetric per-tensor int8 with scale = max|x|/127: values within one
	// step (1.0039...) of the original.
	got := flat(dq)
	for i, v := range vals {
		if math.Abs(got[i]-v) > 127.0/127.0+1e-9 {
			t.Fatalf("element %d: %v, want ~%v", i, got[i], v)
		}
	}
	// Empty input is rejected rather than panicking on xv[0].
	if _, err := QuantizeInt8(newF64(nil, 0), &QParams{}); err == nil {
		t.Fatal("quantizing an empty tensor was accepted")
	}
}

// TestFusedLinearActShapeErrors covers the validation surface.
func TestFusedLinearActShapeErrors(t *testing.T) {
	x := newF64(seq(2, 3), 2, 3)
	w := newF64(seq(4, 3), 4, 3)
	out := newF64(make([]float64, 8), 2, 4)
	if err := FusedLinearAct(x, w, nil, out, ActReLU); err != nil {
		t.Fatalf("valid shapes: %v", err)
	}
	bad := newF64(make([]float64, 6), 2, 3)
	if err := FusedLinearAct(x, w, nil, bad, ActReLU); err == nil {
		t.Fatal("a mismatched out shape was accepted")
	}
}
