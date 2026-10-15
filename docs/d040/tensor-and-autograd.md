# D-040 Tensor Core and Autograd

## Tensor core (verified)

- Storage-backed values with shape, strides, and offset. `Reshape`,
  `Transpose`, `Slice`, `Expand` are zero-copy views; `Contiguous()`
  materializes; `EqualModelOutputs`, `CloseStorage`, `DeepCopy`,
  `Serialize` round-trip exist.
- 15 dtypes: float32/64, complex64/128, int8/16/32/64, uint*, bool, bfloat16.
- Arithmetic is float64-only: int/bool inputs are refused with typed
  errors, and bfloat16 arithmetic is explicitly unimplemented.
- Overflow safety: checked allocation (`checkedShapeBytes`); int8/int16/
  bfloat16 saturating add/sub.
- New in this work: `ops.Softmax` (stable, any dim, negative indexing),
  `ops.Concat` (validated, error paths), scalar Add/Sub/Mul/Div.
- Fixed in this work: broadcasting shape computation, reduction traversal
  on non-contiguous views, and the outer-index mapping that panicked when
  reducing dim 0.

## Reduction planning

`PlanReduction` derives strides from the shape, so kernels materialize
non-contiguous inputs first (`contiguousF64`). The plan carries
`OuterOutputDims`, the input->output dim mapping, which differs between
keepDims modes; using input indices against the output shape was a real
panic/incorrect-result bug.

## Autograd (verified)

- Tape records differentiable ops; `Backward` is single-use; unreachable
  nodes contribute zero (stop-gradient semantics); rule-less nodes are
  `CodeUnimplemented` errors.
- Gradient rules implemented and checked against finite differences or
  analytic values: Add, Sub, Mul, Div, Neg, MatMul, Sum, Mean, Scale,
  Relu, Sigmoid, Tanh, Exp.
- Gradient accumulation is correct for diamond graphs and broadcast
  operands; `Detach` cuts a value out of the graph.
- Optimizers: SGD (momentum, weight decay), Adam (bias-corrected),
  `ZeroGrad` clears gradients and optimizer velocity.
- Documented lifetime rules: a tape belongs to one forward pass; a new
  pass needs a new tape (or `Reset`); parameters are plain tensors owned
  by the model.
