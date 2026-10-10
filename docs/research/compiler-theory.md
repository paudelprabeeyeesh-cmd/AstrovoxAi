# Research Notes — Compiler Theory

> Implementation anchors: `internal/ir`, `internal/lang`,
> `internal/optimizer`, `compiler/`.

## 1. Pipeline

```
source ── lex ──► tokens ── parse ──► AST ── lower ──► HIR/MIR
                                                        │
                                                        ▼
                                              SSA construction
                                                        │
                             ┌───────────┬─────────────┼──────────┬─────────┐
                             ▼           ▼             ▼          ▼         ▼
                          dominators  alias escape   LICM     SCCP     polyhedral
                             │           │             │          │         │
                             ▼           ▼             ▼          ▼         ▼
                             └───────────┴─────────────┴──────────┴─────────┘
                                                        │
                                                        ▼
                                                kernel selection
                                                        │
                                                        ▼
                                                 backend codegen
```

## 2. Analyses Implemented

| Analysis | Where | Classic reference |
|---|---|---|
| Dominator tree | `internal/ir/domfront.go` | Cooper–Harvey–Kennedy |
| Dominance frontier → φ placement | `internal/ir/ssa.go` | Cytron et al. |
| Memory SSA | `internal/ir/memory_ssa.go` | Cytron et al. |
| Alias (Andersen) | `internal/ir/alias.go` | Andersen 1994 |
| Escape analysis | `internal/ir/escape.go` | Choi et al. |
| LICM | `internal/ir/licm.go` | Morel–Renvoise (PRE) family |
| GVN | `internal/ir/gvn.go` |Click hash-value numbering |
| PRE | `internal/ir/pre.go` | Morel–Renvoise 1979 |
| SCCP | `internal/ir/sccp.go` | Wegman–Zadeck |
| Polyhedral | `internal/ir/polyhedral.go` | ISL |
| Loop unrolling / vectorization cost | `tensor/math/auto_vec.go` | Allen & Kennedy |

## 3. The Mini Language (`internal/lang`)

A complete language front end built for the roadmap: lexer → recursive-descent
parser with precedence climbing → AST → optimizer → code generator emitting
**LLVM IR**, **C**, or **WebAssembly** text. Optimizations include constant
folding, algebraic identities, dead-code elimination, and strength reduction.

## 4. Why Not Just Use LLVM?

The roadmap deliberately keeps ownership of the IR and passes so that
tensor-specific lowering (fusion, quantization, layout) can be first-class in the
same pipeline that would otherwise hand off to a generic be backend.