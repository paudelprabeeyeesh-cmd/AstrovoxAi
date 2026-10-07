package compiler

import (
	"math"

	"github.com/astrovox/astrovox/internal/errors"
)

// tval is an interpreter value: a flat buffer
// plus its shape.
type tval struct {
	data  []float64
	shape []int
}

// Interpreter is the reference TIR backend: it
// executes a compiled module directly over the
// TIR AST. It is the fallback and validation
// backend for the JIT pipeline.
type Interpreter struct {
	// MaxIters bounds total loop iterations
	// per Execute call as a runaway guard.
	MaxIters int64
	iters    int64
}

// NewInterpreter creates an interpreter.
func NewInterpreter() *Interpreter {
	return &Interpreter{MaxIters: 1 << 32}
}

// Execute runs the named function with the given
// parameter buffers and returns the output
// buffer data. Buffers map name -> flat slice;
// shapes come from the module signature.
func (it *Interpreter) Execute(mod *Module, fnName string, params map[string][]float64) (map[string][]float64, error) {
	f, ok := mod.Get(fnName)
	if !ok {
		return nil, errors.New(errors.CodeNotFound, "function not found").
			WithField("name", fnName)
	}
	it.iters = 0
	env := map[string]tval{}
	for _, p := range f.Params {
		data, ok := params[p.Name]
		if !ok {
			return nil, errors.New(errors.CodeInvalidArgument, "missing parameter").
				WithField("name", p.Name)
		}
		if len(data) != p.Elements() {
			return nil, errors.New(errors.CodeInvalidArgument, "parameter length mismatch").
				WithField("name", p.Name).
				WithField("got", len(data)).
				WithField("want", p.Elements())
		}
		env[p.Name] = tval{data: data, shape: p.Shape}
	}
	out := tval{data: make([]float64, f.Output.Elements()), shape: f.Output.Shape}
	env[f.Output.Name] = out
	if err := it.execBlock(f.Body, env); err != nil {
		return nil, err
	}
	return map[string][]float64{f.Output.Name: env[f.Output.Name].data}, nil
}

// execBlock executes a statement list.
func (it *Interpreter) execBlock(body []Stmt, env map[string]tval) error {
	for _, s := range body {
		if err := it.execStmt(s, env); err != nil {
			return err
		}
	}
	return nil
}

// execStmt executes one statement.
func (it *Interpreter) execStmt(s Stmt, env map[string]tval) error {
	switch t := s.(type) {
	case AllocateStmt:
		if _, ok := env[t.Buffer.Name]; !ok {
			env[t.Buffer.Name] = tval{
				data:  make([]float64, t.Buffer.Elements()),
				shape: t.Buffer.Shape,
			}
		}
		return nil
	case StoreStmt:
		val, err := it.eval(t.Val, env)
		if err != nil {
			return err
		}
		idx, err := it.evalIdx(t.Idx, env)
		if err != nil {
			return err
		}
		buf, ok := env[t.Name]
		if !ok {
			return errors.New(errors.CodeNotFound, "unknown buffer").
				WithField("name", t.Name)
		}
		off, err := flatIndex(idx, buf.shape, len(buf.data))
		if err != nil {
			return errors.Wrap(err, errors.CodeInvalidArgument, "store").
				WithField("name", t.Name)
		}
		buf.data[off] = val
		return nil
	case ForStmt:
		start := t.Start
		end, err := it.evalInt(t.End, env)
		if err != nil {
			return err
		}
		for i := start; i < end; i++ {
			it.iters++
			if it.iters > it.MaxIters {
				return errors.New(errors.CodeResourceExhausted, "loop iteration bound exceeded")
			}
			env[t.Var] = tval{data: []float64{float64(i)}, shape: []int{}}
			if err := it.execBlock(t.Body, env); err != nil {
				return err
			}
		}
		return nil
	case LetStmt:
		v, err := it.eval(t.Val, env)
		if err != nil {
			return err
		}
		env[t.Name] = tval{data: []float64{v}, shape: []int{}}
		return nil
	case ReturnStmt:
		return nil
	default:
		return errors.New(errors.CodeInvalidArgument, "unknown statement")
	}
}

// eval evaluates an expression to a float64.
func (it *Interpreter) eval(e Expr, env map[string]tval) (float64, error) {
	switch t := e.(type) {
	case ConstExpr:
		return t.Value, nil
	case VarExpr:
		v, ok := env[t.Name]
		if !ok {
			return 0, errors.New(errors.CodeNotFound, "unknown name").
				WithField("name", t.Name)
		}
		if len(t.Idx) == 0 {
			if len(v.data) == 0 {
				return 0, errors.New(errors.CodeInvalidArgument, "empty scalar").
					WithField("name", t.Name)
			}
			return v.data[0], nil
		}
		idx, err := it.evalIdx(t.Idx, env)
		if err != nil {
			return 0, err
		}
		off, err := flatIndex(idx, v.shape, len(v.data))
		if err != nil {
			return 0, errors.Wrap(err, errors.CodeInvalidArgument, "load").
				WithField("name", t.Name)
		}
		return v.data[off], nil
	case BinaryExpr:
		l, err := it.eval(t.Left, env)
		if err != nil {
			return 0, err
		}
		r, err := it.eval(t.Right, env)
		if err != nil {
			return 0, err
		}
		switch t.Op {
		case "+":
			return l + r, nil
		case "-":
			return l - r, nil
		case "*":
			return l * r, nil
		case "/":
			if r == 0 {
				return 0, errors.New(errors.CodeInvalidArgument, "division by zero")
			}
			return l / r, nil
		case "max":
			return math.Max(l, r), nil
		case "min":
			return math.Min(l, r), nil
		default:
			return 0, errors.New(errors.CodeInvalidArgument, "unknown binary op").
				WithField("op", t.Op)
		}
	case CallExpr:
		args := make([]float64, 0, len(t.Args))
		for _, a := range t.Args {
			v, err := it.eval(a, env)
			if err != nil {
				return 0, err
			}
			args = append(args, v)
		}
		switch t.Op {
		case "exp":
			return math.Exp(args[0]), nil
		case "log":
			return math.Log(args[0]), nil
		case "sqrt":
			return math.Sqrt(args[0]), nil
		case "tanh":
			return math.Tanh(args[0]), nil
		case "sigmoid":
			return 1 / (1 + math.Exp(-args[0])), nil
		case "relu":
			return math.Max(0, args[0]), nil
		default:
			return 0, errors.New(errors.CodeInvalidArgument, "unknown call op").
				WithField("op", t.Op)
		}
	case ReduceExpr:
		return it.evalReduce(t, env)
	default:
		return 0, errors.New(errors.CodeInvalidArgument, "unknown expression")
	}
}

// evalReduce evaluates a reduction expression.
func (it *Interpreter) evalReduce(r ReduceExpr, env map[string]tval) (float64, error) {
	buf, ok := env[r.Src]
	if !ok {
		return 0, errors.New(errors.CodeNotFound, "unknown buffer").
			WithField("name", r.Src)
	}
	acc := r.Init
	axis := r.Axes[0]
	for k := 0; k < buf.shape[axis]; k++ {
		it.iters++
		if it.iters > it.MaxIters {
			return 0, errors.New(errors.CodeResourceExhausted, "loop iteration bound exceeded")
		}
		// Bind the reduction loop variable.
		env["r"] = tval{data: []float64{float64(k)}, shape: []int{}}
		idx, err := it.evalIdx(r.SrcIdx, env)
		if err != nil {
			return 0, err
		}
		off, err := flatIndex(idx, buf.shape, len(buf.data))
		if err != nil {
			return 0, errors.Wrap(err, errors.CodeInvalidArgument, "reduce load")
		}
		v := buf.data[off]
		switch r.Op {
		case "sum":
			acc += v
		case "prod":
			acc *= v
		case "max":
			if v > acc {
				acc = v
			}
		case "min":
			if v < acc {
				acc = v
			}
		default:
			return 0, errors.New(errors.CodeInvalidArgument, "unknown reduce op").
				WithField("op", r.Op)
		}
	}
	return acc, nil
}

// evalIdx evaluates index expressions.
func (it *Interpreter) evalIdx(idx []Expr, env map[string]tval) ([]int, error) {
	out := make([]int, 0, len(idx))
	for _, e := range idx {
		v, err := it.eval(e, env)
		if err != nil {
			return nil, err
		}
		out = append(out, int(v))
	}
	return out, nil
}

// evalInt evaluates an expression as an integer.
func (it *Interpreter) evalInt(e Expr, env map[string]tval) (int, error) {
	v, err := it.eval(e, env)
	if err != nil {
		return 0, err
	}
	return int(v), nil
}

// flatIndex computes the row-major offset.
func flatIndex(idx, shape []int, bufLen int) (int, error) {
	if len(idx) != len(shape) {
		return 0, errors.New(errors.CodeInvalidArgument, "index rank mismatch").
			WithField("idx", len(idx)).WithField("shape", len(shape))
	}
	off := 0
	for d := range idx {
		if idx[d] < 0 || idx[d] >= shape[d] {
			return 0, errors.New(errors.CodeInvalidArgument, "index out of bounds").
				WithField("dim", d).WithField("idx", idx[d]).
				WithField("extent", shape[d])
		}
		off = off*shape[d] + idx[d]
	}
	if off >= bufLen {
		return 0, errors.New(errors.CodeInvalidArgument, "flat offset out of bounds").
			WithField("off", off).WithField("len", bufLen)
	}
	return off, nil
}

// expConst folds exp at compile time.
func expConst(x float64) float64 { return math.Exp(x) }

// sqrtConst folds sqrt at compile time.
func sqrtConst(x float64) float64 { return math.Sqrt(x) }
