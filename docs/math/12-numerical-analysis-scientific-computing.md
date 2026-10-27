# Section 12 — Numerical Analysis and Scientific Computing

**Level 4–5** | Topics 457–491  
**Used in AstraVox:** reliable computation, GPU performance, large-model training, low-precision inference, detecting when numerical errors invalidate results.

457. Floating-point representation  
458. Floating-point rounding  
459. Cancellation error  
460. Numerical stability  
461. Error propagation  
462. Conditioning and ill-conditioned problems  
463. Numerical root finding  
464. Bisection method  
465. Newton–Raphson method  
466. Secant method  
467. Fixed-point iteration  
468. Numerical differentiation  
469. Numerical integration  
470. Interpolation  
471. Polynomial approximation  
472. Least-squares approximation  
473. Numerical solutions of linear systems  
474. Iterative linear solvers  
475. Conjugate gradient  
476. GMRES and Krylov-subspace methods  
477. Numerical eigenvalue algorithms  
478. Sparse numerical computation  
479. Monte Carlo integration  
480. Quasi-Monte Carlo methods  
481. Randomized numerical linear algebra  
482. Numerical ordinary differential equations  
483. Finite-difference methods  
484. Finite-element methods  
485. Finite-volume methods  
486. Spectral methods  
487. Stability of numerical schemes  
488. Automatic mixed precision  
489. Quantization error  
490. Numerical reproducibility  
491. Parallel numerical algorithms  

## AI applications

Reliable computation, GPU performance, large-model training, low-precision inference, and detecting when numerical errors invalidate results.

## Mapping to code

- `tensor/math/` — floating-point rounding, cancellation error, stability, conditioning, root finding, integration, interpolation, linear solvers, conjugate gradient, GMRES, eigenvalue algorithms, sparse computation, mixed precision, quantization error, reproducibility (topics 457–491; implemented in `gemm.go`, `norm.go`, `fft.go`, `quant.go`, `fused_act.go`, `simd.go`, `winograd.go`, `flash_attention.go`).
- `internal/inference/` — automatic mixed precision, quantization, parallel numerical algorithms (topics 488–491).
