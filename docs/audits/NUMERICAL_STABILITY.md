# Numerical Stability Audit — AstrovoxAI Math Engine

**Auditor role:** Numerical-analysis verification engineer  
**Date:** 2026-10-27  
**Environment:** Windows, Python 3.14, numpy 2.5.3, sympy 1.14.0, ~4 GB RAM  
**Verification suite:** `math_engine/tests/verification/test_independent_verification.py`

---

## Scope

Numerical stability of the actually-implemented operations (Sections S1–S12, S14–S16, S18–S19). Lightweight mode: no GPU, no scipy/sklearn, numpy+sympy only.

---

## Stability findings by domain

### Floating-point representation & rounding (S1 topics 19, 20, 25)

- **Scientific notation:** correctly extracts mantissa/exponent via `log10`; handles 0 and negative values; mantissa normalized to `[1,10)`.
- **Significant figures:** uses `floor(log10(abs(x)))` scaling; guards `x==0`.
- **Rounding error:** reports `abs(x - round(x, d))`; no cancellation in the subtraction itself for typical inputs.

**Assessment:** Stable for the implemented operations. No catastrophic-cancellation exposure in the exposed paths.

### Root finding (S12: bisection, Newton–Raphson)

- **Bisection:** brackets `[a,b]` required with `f(a)·f(b) ≤ 0`; validated. Converges linearly; tolerance on `|f(mid)|` and interval width. Tested: `x²−2` on `[1,2]` → root² ≈ 2 (tol 1e-4). **Stable.**
- **Newton–Raphson:** requires `f'` and `f'(x) ≠ 0`; tested `x²−2` from `x0=1` → root² ≈ 2 (tol 1e-6). No damping/line-search; can diverge for poor initial guesses or near-stationary points (documented limitation, not a crash). **Stable when bracket/derivative well-behaved.**

### Numerical integration (S12: trapezoidal)

- Composite trapezoidal rule with `n` subintervals. Tested `∫₀¹ x dx = 0.5` (tol 1e-3, n=1000). **Stable** for smooth functions; no adaptive refinement or singularity handling (documented limitation).

### Linear systems (S12: Gaussian elimination; S5: solve, inverse)

- **Gaussian elimination:** partial pivoting by max-abs column; singularity detected at `|pivot| < 1e-14`. Tested `A·x = b` residual `≈ 0` (atol 1e-8). **Stable** due to partial pivoting.
- **Matrix inverse (`mat_inv`):** uses `np.linalg.inv` with `LinAlgError` → `DomainError` for singular matrices. Tested `A·A⁻¹ ≈ I` (atol 1e-9). **Stable** for well-conditioned matrices; ill-conditioned inputs produce large errors (no condition-number guard on inverse itself — `mat_norm` reports condition number separately).
- **Determinant:** `np.linalg.det`; singular flagged at `|det| < 1e-12`.

### Linear algebra decompositions (S5)

- **Eigendecomposition:** `np.linalg.eig`; verified `A·v ≈ λ·v` (atol 1e-6). Complex eigenvalues handled; not sorted (documented).
- **SVD:** `np.linalg.svd`; verified `U·S·Vᵀ ≈ A` (atol 1e-8). **Stable** — SVD is the most stable decomposition.
- **PCA:** `eigh` on covariance matrix; projection `Xc @ components`. Stable for centered data.
- **Low-rank approximation:** truncated SVD; Frobenius-error check confirms energy capture. **Stable.**
- **Norms / condition number:** `np.linalg.norm`, `np.linalg.cond`; condition number reported (may be `inf` for singular).

### Calculus (S6)

- **Derivatives:** sympy symbolic differentiation, cross-checked against central finite difference (`h=1e-6`, tolerance 1e-4). Tested `x²` at 3 → 6, `sin(x)` at 0 → 1. **Stable** for smooth expressions; finite-difference check has O(h²) truncation + roundoff tradeoff (documented).
- **Integration:** sympy symbolic for indefinite; numeric definite integration via sympy `integrate` over interval. Tested exact values. Stable.
- **Autograd demo:** central finite difference (not the `astrovox/autograd` engine). Gradient of `x²+y²` at `[3,4]` → `[6,8]` (tol 1e-4). **Stable** for small `h`.

### Probability & statistics (S8, S9)

- **Distributions:** Bernoulli/binomial PMFs use `math.comb` (exact integer arithmetic → stable). Normal PDF uses `exp(−0.5·((x−μ)/σ)²)` with `σ > 0` guard; no overflow for typical inputs. **Stable.**
- **Expectation/variance:** `Σ p·x` and `Σ p·(x−μ)²`; requires probabilities sum to 1 (validated). **Stable.**
- **Linear regression:** closed-form slope/intercept; guards zero-variance `x` (`DomainError`). R² computed from residuals. **Stable** for non-degenerate `x`.
- **CI / z-test:** standard-error based; z-test uses normal approximation. **Stable** for n ≥ 2.
- **ANOVA:** one-way, guards groups with < 2 points. **Stable.**

### Information theory (S10)

- **Entropy:** `−Σ p·log_b(p)` with `p·log(p)` defined as 0 when `p=0` (avoids `log(0)`). Base validated `> 0`, `≠ 1`. **Stable.**
- **Cross-entropy:** `−Σ p·log q`; returns `DomainError` (infinite) when `q=0` and `p>0` (support mismatch) instead of producing `inf` silently. **Stable and safe.**
- **KL divergence:** `Σ p·log(p/q)`; `DomainError` on support mismatch; verified KL(p||p)=0 and KL≥0. **Stable.**
- **Perplexity:** `b^H`; stable given finite entropy.
- **Huffman:** heap-based; prefix property verified; average length ≥ entropy (Kraft inequality). **Stable.**

### Deep learning (S15)

- **Softmax:** subtracts row max before `exp` (standard stability trick); verified sums to 1. **Stable.**
- **Sigmoid:** `1/(1+exp(−x))` with input clipped to `[-500, 500]` to avoid overflow. **Stable.**
- **ReLU / batch norm:** ReLU exact; batch norm divides by `sqrt(var + eps)` with `eps>0`; output mean≈0, var≈1 (within eps). **Stable.**
- **Backprop scalar:** gradient of `0.5·error²` (factor-of-2 convention vs full MSE — documented). Stable for single step.

### Transformers (S16)

- **Scaled dot-product attention:** scales by `1/√dk`, subtracts row max before softmax. Verified output and weight sum=1. **Stable.**
- **Top-k / top-p (nucleus):** renormalize selected probabilities to sum 1. Verified. **Stable.**
- **Perplexity:** `exp(−avg logprob)`; stable for finite logprobs.

### Optimization (S7)

- **Gradient descent:** fixed `lr`, stopping on parameter change `< tol`. Tested convergence to `x=3` for `(x−3)²`. No momentum/adaptive logic in this path (Adam is separate). **Stable** for convex, well-scaled problems; can overshoot for large `lr`.
- **Adam step:** bias-corrected moments; `eps` in denominator. Verified exact update. **Stable** for one step.

---

## Known numerical limitations (documented, not crashes)

| Limitation | Impact | Mitigation status |
|------------|--------|-------------------|
| No `scipy`/`sklearn` installed | Richer distributions/tests unavailable | Pure numpy/sympy implementations |
| Newton–Raphson no damping | Can diverge on bad initial guess | Input validation only; documented |
| Trapezoidal rule non-adaptive | Poor for singular/oscillatory integrands | Fixed `n`; documented |
| Matrix inverse has no condition guard | Ill-conditioned → large errors | `mat_norm` reports cond separately |
| Finite-difference derivative | O(h²) truncation + roundoff | Tolerance 1e-4; documented |
| `*args` functions not dispatchable via `**kwargs` | e.g. `anova_one_way(*groups)` | Direct call workaround; dispatcher limitation |
| Section 13/17 entirely unimplemented | No numerical PDE/ODE or search code | Not implemented (planned) |

---

## Resource profile (4 GB RAM lightweight mode)

- No GPU (`enable_gpu=False`).
- No heavyweight framework imports at module load (lazy optional deps).
- Input-size limits in `math_engine/core/limits.py`: max matrix dim 2048, max tensor elements 1e6, max iterations 100000, max polynomial degree 512.
- All verification tests run in < 12 seconds, low memory.

---

## Conclusion

The implemented operations are **numerically stable** for their validated domains, with appropriate domain guards (division by zero, log of negative, singular matrices, support mismatch, shape mismatch, invalid bases) producing structured errors rather than wrong answers or crashes. The main gaps are **coverage** (many topics unimplemented) and **advanced numerical features** (adaptive integration, damped optimization, condition-guarded inversion), not instability in what exists.
