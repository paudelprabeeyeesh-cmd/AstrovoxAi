package compiler

import (
	"fmt"

	"github.com/astrovox/astrovox/graph"
	"github.com/astrovox/astrovox/internal/errors"
)

// Lower transforms a validated computational
// graph into a TIR module. Each op becomes a
// TIR function; elementwise ops lower to pointwise
// loops, matmul to tiled triple loops, and
// reductions to reduction loops.
type Lowerer struct {
	counter int
}

// NewLowerer creates a lowerer.
func NewLowerer() *Lowerer { return &Lowerer{} }

// Lower compiles the graph into a TIR module.
func (l *Lowerer) Lower(g *graph.Graph) (*Module, error) {
	if g == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil graph")
	}
	if err := g.Validate(); err != nil {
		return nil, err
	}
	order, err := g.TopologicalSort()
	if err != nil {
		return nil, err
	}
	mod := NewModule()
	env := map[int]string{} // node ID -> buffer name
	for _, id := range order {
		n, err := g.Node(id)
		if err != nil {
			return nil, err
		}
		name, fn, err := l.lowerNode(g, n, env)
		if err != nil {
			return nil, errors.Wrap(err, errors.CodeInternal, "lowering failed").
				WithField("node", n.ID).WithField("op", n.Op.Name())
		}
		env[n.ID] = name
		mod.Add(fn)
	}
	return mod, nil
}

// LowerSingle compiles the entire graph
// into one TIR function: source nodes
// become parameters, intermediate node
// outputs become allocations, and the
// sink node output becomes the function
// result. Parameter names are
// "input_<nodeID>".
func (l *Lowerer) LowerSingle(g *graph.Graph) (*Func, error) {
	if g == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil graph")
	}
	if err := g.Validate(); err != nil {
		return nil, err
	}
	order, err := g.TopologicalSort()
	if err != nil {
		return nil, err
	}
	env := map[int]string{}
	var params []Buffer
	var body []Stmt
	for _, id := range order {
		n, err := g.Node(id)
		if err != nil {
			return nil, err
		}
		if len(n.Inputs) == 0 {
			// Source node: becomes a function parameter.
			name := fmt.Sprintf("input_%d", n.ID)
			env[n.ID] = name
			params = append(params, Buffer{
				Name:  name,
				Shape: n.OutShapes()[0].Dims(),
				DType: "float64",
			})
			continue
		}
		name, fn, err := l.lowerNode(g, n, env)
		if err != nil {
			return nil, errors.Wrap(err, errors.CodeInternal, "lowering failed").
				WithField("node", n.ID).WithField("op", n.Op.Name())
		}
		env[n.ID] = name
		body = append(body, fn.Body...)
	}
	// The sink node (no outputs) defines the result.
	var out Buffer
	for _, id := range order {
		n, err := g.Node(id)
		if err != nil {
			return nil, err
		}
		if len(n.Outputs) == 0 {
			out = Buffer{
				Name:  env[id],
				Shape: n.OutShapes()[0].Dims(),
				DType: "float64",
			}
			break
		}
	}
	if out.Name == "" {
		return nil, errors.New(errors.CodeInvalidArgument, "graph has no sink node")
	}
	return &Func{
		Name:   "main",
		Params: params,
		Output: out,
		Body:   body,
		Source: "graph",
	}, nil
}

// lowerNode lowers one graph node to a TIR function.
func (l *Lowerer) lowerNode(g *graph.Graph, n *graph.Node, env map[int]string) (string, *Func, error) {
	l.counter++
	fnName := fmt.Sprintf("f%d_%s", n.ID, sanitize(n.Op.Name()))
	var inputs []Buffer
	for _, eid := range n.Inputs {
		e := g.Edges()[eid]
		src, err := g.Node(e.From)
		if err != nil {
			return "", nil, err
		}
		inputs = append(inputs, Buffer{
			Name:  env[e.From],
			Shape: src.OutShapes()[e.FromPort].Dims(),
			DType: "float64",
		})
	}
	outShape := n.OutShapes()[0].Dims()
	out := Buffer{
		Name:  fnName + "_out",
		Shape: outShape,
		DType: "float64",
	}
	body, err := l.lowerOp(n.Op.Name(), inputs, out)
	if err != nil {
		return "", nil, err
	}
	fn := &Func{
		Name:   fnName,
		Params: inputs,
		Output: out,
		Body:   body,
		Source: n.Op.Name(),
	}
	return out.Name, fn, nil
}

// lowerOp emits TIR statements for one op.
func (l *Lowerer) lowerOp(opName string, inputs []Buffer, out Buffer) ([]Stmt, error) {
	switch {
	case opName == "matmul" || opName == "gemm":
		return l.lowerMatMul(inputs, out), nil
	case isReduction(opName):
		stmts, err := l.lowerReduce(opName, inputs, out)
		if err != nil {
			return nil, err
		}
		return stmts, nil
	case isElementwise(opName):
		stmts, err := l.lowerElementwise(opName, inputs, out)
		if err != nil {
			return nil, err
		}
		return stmts, nil
	default:
		return nil, errors.New(errors.CodeUnimplemented, "no TIR lowering for op").
			WithField("op", opName)
	}
}

// lowerElementwise emits pointwise loops over the
// output shape with broadcasting over singleton
// input dims.
func (l *Lowerer) lowerElementwise(opName string, inputs []Buffer, out Buffer) ([]Stmt, error) {
	if len(inputs) == 0 {
		return nil, errors.New(errors.CodeInvalidArgument, "elementwise op needs inputs").
			WithField("op", opName)
	}
	var body []Stmt
	body = append(body, AllocateStmt{Buffer: out})
	rank := len(out.Shape)
	// Build the value expression.
	var val Expr
	switch opName {
	case "add":
		val = BinaryExpr{Op: "+",
			Left:  loadBroadcast(inputs[0], out.Shape, idxVars(rank)),
			Right: loadBroadcast(inputs[1], out.Shape, idxVars(rank))}
	case "sub":
		val = BinaryExpr{Op: "-",
			Left:  loadBroadcast(inputs[0], out.Shape, idxVars(rank)),
			Right: loadBroadcast(inputs[1], out.Shape, idxVars(rank))}
	case "mul":
		val = BinaryExpr{Op: "*",
			Left:  loadBroadcast(inputs[0], out.Shape, idxVars(rank)),
			Right: loadBroadcast(inputs[1], out.Shape, idxVars(rank))}
	case "div":
		val = BinaryExpr{Op: "/",
			Left:  loadBroadcast(inputs[0], out.Shape, idxVars(rank)),
			Right: loadBroadcast(inputs[1], out.Shape, idxVars(rank))}
	case "neg":
		val = BinaryExpr{Op: "-", Left: ConstExpr{Value: 0},
			Right: loadBroadcast(inputs[0], out.Shape, idxVars(rank))}
	case "exp", "log", "sqrt", "tanh", "sigmoid", "relu":
		val = CallExpr{Op: opName,
			Args: []Expr{loadBroadcast(inputs[0], out.Shape, idxVars(rank))}}
	default:
		return nil, errors.New(errors.CodeUnimplemented, "unknown elementwise op").
			WithField("op", opName)
	}
	// Emit nested loops over output dims.
	stmts := []Stmt{StoreStmt{Name: out.Name, Idx: idxVars(rank), Val: val}}
	for d := rank - 1; d >= 0; d-- {
		stmts = []Stmt{ForStmt{Var: fmt.Sprintf("i%d", d), Start: 0, End: ConstExpr{Value: float64(out.Shape[d])}, Body: stmts}}
	}
	body = append(body, stmts...)
	return body, nil
}

// lowerMatMul emits triple loops:
// for i, j, k: out[i,j] += A[i,k] * B[k,j].
func (l *Lowerer) lowerMatMul(inputs []Buffer, out Buffer) []Stmt {
	a, b := inputs[0], inputs[1]
	var body []Stmt
	body = append(body, AllocateStmt{Buffer: out})
	// Build the accumulate expression:
	// out[i,j] = out[i,j] + A[i,k] * B[k,j].
	outIdx := []Expr{VarExpr{Name: "i"}, VarExpr{Name: "j"}}
	aIdx := []Expr{VarExpr{Name: "i"}, VarExpr{Name: "k"}}
	bIdx := []Expr{VarExpr{Name: "k"}, VarExpr{Name: "j"}}
	prod := BinaryExpr{Op: "*",
		Left:  VarExpr{Name: a.Name, Idx: aIdx},
		Right: VarExpr{Name: b.Name, Idx: bIdx}}
	acc := BinaryExpr{Op: "+",
		Left:  VarExpr{Name: out.Name, Idx: outIdx},
		Right: prod}
	store := StoreStmt{Name: out.Name, Idx: outIdx, Val: acc}
	inner := []Stmt{store}
	for _, loop := range []struct {
		v   string
		end Expr
	}{
		{"k", ConstExpr{Value: float64(a.Shape[1])}},
		{"j", ConstExpr{Value: float64(b.Shape[1])}},
		{"i", ConstExpr{Value: float64(a.Shape[0])}},
	} {
		inner = []Stmt{ForStmt{Var: loop.v, Start: 0, End: loop.end, Body: inner}}
	}
	body = append(body, inner...)
	return body
}

// lowerReduce emits reduction loops.
func (l *Lowerer) lowerReduce(opName string, inputs []Buffer, out Buffer) ([]Stmt, error) {
	src := inputs[0]
	var op string
	var init float64
	switch opName {
	case "sum":
		op, init = "sum", 0
	case "prod":
		op, init = "prod", 1
	case "max":
		op, init = "max", negInf
	case "min":
		op, init = "min", inf
	default:
		return nil, errors.New(errors.CodeUnimplemented, "unknown reduction").
			WithField("op", opName)
	}
	var body []Stmt
	body = append(body, AllocateStmt{Buffer: out})
	rank := len(out.Shape)
	// Reduce over the trailing axis by default.
	reduceAxis := len(src.Shape) - 1
	var val Expr
	val = ReduceExpr{
		Op: op, Src: src.Name,
		SrcIdx: reduceIdx(src.Shape, out.Shape, rank, reduceAxis),
		Axes:   []int{reduceAxis},
		Init:   init,
	}
	stmts := []Stmt{StoreStmt{Name: out.Name, Idx: idxVars(rank), Val: val}}
	for d := rank - 1; d >= 0; d-- {
		stmts = []Stmt{ForStmt{Var: fmt.Sprintf("i%d", d), Start: 0, End: ConstExpr{Value: float64(out.Shape[d])}, Body: stmts}}
	}
	body = append(body, stmts...)
	return body, nil
}

// reduceIdx builds the source index expression:
// output indices for kept dims, a VarExpr over
// the reduced axis.
func reduceIdx(srcShape, outShape []int, rank, reduceAxis int) []Expr {
	idx := make([]Expr, len(srcShape))
	oi := 0
	for d := range srcShape {
		if d == reduceAxis {
			idx[d] = VarExpr{Name: "r"}
		} else {
			idx[d] = VarExpr{Name: fmt.Sprintf("i%d", oi)}
			oi++
		}
	}
	return idx
}

// loadBroadcast emits a VarExpr with broadcast
// index expressions for singleton input dims.
func loadBroadcast(src Buffer, outShape []int, idx []Expr) Expr {
	sidx := make([]Expr, len(src.Shape))
	off := len(outShape) - len(src.Shape)
	for d := range src.Shape {
		if src.Shape[d] == 1 {
			sidx[d] = ConstExpr{Value: 0}
		} else {
			sidx[d] = idx[off+d]
		}
	}
	return VarExpr{Name: src.Name, Idx: sidx}
}

// idxVars creates loop-variable expressions for
// the given rank.
func idxVars(rank int) []Expr {
	out := make([]Expr, rank)
	for d := 0; d < rank; d++ {
		out[d] = VarExpr{Name: fmt.Sprintf("i%d", d)}
	}
	return out
}

// sanitize makes an op name identifier-safe.
func sanitize(s string) string {
	out := make([]rune, 0, len(s))
	for _, r := range s {
		if r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' || r >= '0' && r <= '9' {
			out = append(out, r)
		} else {
			out = append(out, '_')
		}
	}
	return string(out)
}

const inf = 1.797693134862315708145274237317043567981e+308

const negInf = -inf

// isElementwise reports whether the op lowers to
// pointwise loops.
func isElementwise(op string) bool {
	switch op {
	case "add", "sub", "mul", "div", "neg",
		"exp", "log", "sqrt", "tanh", "sigmoid", "relu":
		return true
	}
	return false
}

// isReduction reports whether the op lowers to
// reduction loops.
func isReduction(op string) bool {
	switch op {
	case "sum", "prod", "max", "min", "mean":
		return true
	}
	return false
}
