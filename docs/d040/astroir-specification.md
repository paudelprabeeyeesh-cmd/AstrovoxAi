# D-040 AstroIR Specification (as implemented)

AstroIR, as it exists in this repository, is the compiler's TIR: a
three-address, loop-nest intermediate representation produced by lowering
a `graph.Graph`. This document describes the implemented form, not an
aspirational one.

## Structure

- A `Module` holds named functions; each graph compiles to a single
  `main` function.
- Statements: `Assign`, `Load`, `Store`, `For`, `If`, `Return`, ...
- Expressions: typed values, binary/unary ops, calls, index expressions,
  reduce expressions (`Sum`, `Mean`, `Max`, `Min`, `Any`) with
  user-supplied fold functions.
- Source nodes of the graph become parameters named `input_<nodeID>`;
  the sink node becomes the result.

## Validation and optimization

- `compiler.Compile` with the interpreter target lowers, then runs the TIR
  optimizer (constant folding, dead-node elimination, fusion). The
  optimizer is equivalence-tested against unoptimized execution
  (`compiler/compiler_test.go`: "OptimizedMatchesUnoptimized").
- Graphs are validated by the graph layer: missing inputs, invalid
  references, cycles (rejected at edge insertion), and shape mismatches
  are errors.

## Determinism

- `Serialize`/`Deserialize` for TIR are byte-deterministic.
- The acceptance scenario verifies interpreter output equals the autograd
  engine on the same computation within 1e-9.

## What is not AstroIR here

`internal/ir` is a separate SSA-style graph package with real analyses
(dominators, loops, SCCP data structures) but inert optimization passes
and no production importer. It is Experimental; it is not the IR of
record. See engineering-decisions.md ADR-4.
