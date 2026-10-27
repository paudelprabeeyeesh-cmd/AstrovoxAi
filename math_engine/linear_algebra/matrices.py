"""Section 5 — Linear algebra (topics 127-175), reusing numpy + tensor/math where possible."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from math_engine.core.result import MathResult
from math_engine.core.errors import DomainError, ValidationError
from math_engine.core.validation import require_finite, require_positive, require_non_negative


def _result(topic_id: str, op: str, value: Any, steps: list[str] | None = None, **kw) -> MathResult:
    return MathResult(topic_id=topic_id, operation_id=op, status="implemented",
                      result=value, steps=steps or [], verified=True, **kw)


def _mat(data: Any) -> np.ndarray:
    try:
        return np.array(data, dtype=np.float64)
    except (ValueError, TypeError) as exc:
        raise ValidationError(f"Cannot convert to matrix: {data!r}") from exc


# Topic 128: Vector addition / scalar multiplication
def vector_op(v1: Any, v2: Any | None = None, op: str = "add", scalar: Any = 1.0) -> MathResult:
    a = _mat(v1)
    if a.ndim != 1:
        raise ValidationError("Input must be a 1-D vector")
    if op == "add":
        if v2 is None:
            raise ValidationError("vector2 required for add")
        b = _mat(v2)
        if a.shape != b.shape:
            raise ValidationError("Vectors must have same shape")
        res = a + b
    elif op == "scale":
        s = require_finite(scalar, "scalar")
        res = a * s
    else:
        raise ValidationError("Unsupported vector op")
    return _result("S5.T128", "vector_op",
                   {"op": op, "result": res.tolist(), "shape": res.shape},
                   steps=[f"Vector {op}: {a.tolist()} -> {res.tolist()}"])


# Topic 129: Dot product and norm
def dot_norm(v1: Any, v2: Any) -> MathResult:
    a = _mat(v1); b = _mat(v2)
    if a.shape != b.shape or a.ndim != 1:
        raise ValidationError("Need two 1-D vectors of same shape")
    dot = float(np.dot(a, b))
    na = float(np.linalg.norm(a)); nb = float(np.linalg.norm(b))
    return _result("S5.T129", "dot_norm",
                   {"dot": dot, "norm_v1": na, "norm_v2": nb},
                   steps=[f"dot = {dot}", f"||v1|| = {na}, ||v2|| = {nb}"])


# Topic 131: Matrix multiplication
def mat_mul(a: Any, b: Any) -> MathResult:
    A = _mat(a); B = _mat(b)
    if A.ndim != 2 or B.ndim != 2:
        raise ValidationError("Both inputs must be 2-D matrices")
    if A.shape[1] != B.shape[0]:
        raise ValidationError(f"Shape mismatch: {A.shape} x {B.shape}")
    res = A @ B
    return _result("S5.T131", "mat_mul",
                   {"result": res.tolist(), "shape": res.shape},
                   steps=[f"Matrix multiply {A.shape} @ {B.shape} = {res.shape}"])


# Topic 132: Transpose and identity
def transpose(a: Any) -> MathResult:
    A = _mat(a)
    return _result("S5.T132", "transpose",
                   {"result": A.T.tolist(), "shape": A.T.shape},
                   steps=[f"Transpose {A.shape} -> {A.T.shape}"])


def identity(n: Any) -> MathResult:
    N = int(require_positive(require_finite(n, "n"), "n"))
    return _result("S5.T132", "identity",
                   {"result": np.eye(N).tolist(), "shape": (N, N)},
                   steps=[f"I_{N} created"])


# Topic 133: Matrix inverse
def mat_inv(a: Any) -> MathResult:
    A = _mat(a)
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        raise ValidationError("Matrix must be square")
    try:
        inv = np.linalg.inv(A)
    except np.linalg.LinAlgError as exc:
        raise DomainError("Matrix is singular, cannot invert") from exc
    return _result("S5.T133", "mat_inv",
                   {"result": inv.tolist(), "shape": inv.shape},
                   steps=[f"Inverse of {A.shape} matrix computed"])


# Topic 134: Determinant
def determinant(a: Any) -> MathResult:
    A = _mat(a)
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        raise ValidationError("Matrix must be square")
    det = float(np.linalg.det(A))
    return _result("S5.T134", "determinant",
                   {"determinant": det, "is_singular": abs(det) < 1e-12},
                   steps=[f"det = {det}"])


# Topic 135: Rank
def rank(a: Any) -> MathResult:
    A = _mat(a)
    r = int(np.linalg.matrix_rank(A))
    return _result("S5.T135", "rank",
                   {"rank": r, "shape": A.shape},
                   steps=[f"rank({A.shape}) = {r}"])


# Topic 136: Solve linear system Ax = b
def solve_linear_system(a: Any, b: Any) -> MathResult:
    A = _mat(a); B = _mat(b)
    if A.ndim != 2:
        raise ValidationError("A must be 2-D")
    if A.shape[0] != A.shape[1]:
        raise ValidationError("A must be square")
    try:
        x = np.linalg.solve(A, B)
    except np.linalg.LinAlgError as exc:
        raise DomainError("System has no unique solution") from exc
    return _result("S5.T136", "solve_linear_system",
                   {"solution": x.tolist(), "shape": x.shape},
                   steps=[f"Solved Ax=b, x shape {x.shape}"])


# Topic 145: Eigenvalues/eigenvectors
def eig(a: Any) -> MathResult:
    A = _mat(a)
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        raise ValidationError("Matrix must be square")
    w, v = np.linalg.eig(A)
    return _result("S5.T145", "eig",
                   {"eigenvalues": w.tolist(), "eigenvectors": v.tolist()},
                   steps=[f"Eigenvalues: {w.tolist()}"])


# Topic 150: SVD
def svd(a: Any) -> MathResult:
    A = _mat(a)
    U, S, Vt = np.linalg.svd(A, full_matrices=False)
    return _result("S5.T150", "svd",
                   {"U": U.tolist(), "S": S.tolist(), "Vt": Vt.tolist()},
                   steps=[f"SVD: singular values {S.tolist()}"])


# Topic 154: Matrix norm and condition number
def mat_norm(a: Any, ord: Any = None) -> MathResult:
    A = _mat(a)
    n = float(np.linalg.norm(A, ord=ord))
    cond = None
    if A.ndim == 2 and A.shape[0] == A.shape[1]:
        try:
            cond = float(np.linalg.cond(A))
        except np.linalg.LinAlgError:
            cond = float("inf")
    return _result("S5.T154", "mat_norm",
                   {"norm": n, "condition_number": cond},
                   steps=[f"||A|| = {n}, cond = {cond}"])


# Topic 158: PCA
def pca(data: Any, n_components: Any = 2) -> MathResult:
    X = _mat(data)
    k = int(require_positive(require_finite(n_components, "n_components"), "n_components"))
    Xc = X - X.mean(axis=0, keepdims=True)
    cov = np.cov(Xc, rowvar=False)
    vals, vecs = np.linalg.eigh(cov)
    order = np.argsort(vals)[::-1]
    components = vecs[:, order[:k]]
    projected = Xc @ components
    return _result("S5.T158", "pca",
                   {"components": components.tolist(),
                    "explained_variance": vals[order[:k]].tolist(),
                    "projected": projected.tolist()},
                   steps=[f"PCA: {X.shape} -> {projected.shape}, {k} components"])


# Topic 159: Low-rank approximation via SVD
def low_rank_approx(a: Any, rank: Any) -> MathResult:
    A = _mat(a)
    r = int(require_positive(require_finite(rank, "rank"), "rank"))
    U, S, Vt = np.linalg.svd(A, full_matrices=False)
    r = min(r, len(S))
    approx = (U[:, :r] * S[:r]) @ Vt[:r]
    return _result("S5.T159", "low_rank_approx",
                   {"approximation": approx.tolist(), "rank": r, "singular_values_used": S[:r].tolist()},
                   steps=[f"Low-rank approx rank {r} from {len(S)} singular values"])
