package compiler

import (
	"github.com/astrovox/astrovox/internal/errors"
)

// TIROptimizer applies TIR-level optimizations:
// constant folding, loop-invariant hoisting of
// bounds, dead allocation elimination, and
// store-to-load forwarding.
type TIROptimizer struct {
	passes int
	folds  int
}

// NewTIROptimizer creates an optimizer.
func NewTIROptimizer() *TIROptimizer { return &TIROptimizer{} }

// Optimize runs the pass set to a fixpoint.
// Returns the optimized module plus the pass
// and fold counts.
func (o *TIROptimizer) Optimize(m *Module) (*Module, int, int, error) {
	if m == nil {
		return nil, 0, 0, errors.New(errors.CodeInvalidArgument, "nil module")
	}
	for pass := 0; pass < 8; pass++ {
		changed := false
		for _, name := range m.Order {
			f := m.Funcs[name]
			if f == nil {
				continue
			}
			body, c, fl, err := o.optimizeFunc(f)
			if err != nil {
				return nil, 0, 0, err
			}
			f.Body = body
			if c {
				changed = true
			}
			o.folds += fl
		}
		o.passes++
		if !changed {
			break
		}
	}
	return m, o.passes, o.folds, nil
}

// optimizeFunc runs the function-level passes.
func (o *TIROptimizer) optimizeFunc(f *Func) ([]Stmt, bool, int, error) {
	var changed bool
	var folds int
	body := f.Body
	// Pass 1: constant-fold store values whose
	// expression is fully constant.
	body, c, fl := o.constFoldStores(body)
	changed = changed || c
	folds += fl
	// Pass 2: remove stores into buffers that
	// are never loaded (dead allocation). The
	// function output is always live.
	body, c = o.deadStoreElim(body, f.Output.Name)
	changed = changed || c
	return body, changed, folds, nil
}

// constFoldStores folds constant store values.
// Stores already holding constants are skipped
// so the fixpoint converges in one folding pass.
func (o *TIROptimizer) constFoldStores(body []Stmt) ([]Stmt, bool, int) {
	changed := false
	folds := 0
	out := make([]Stmt, 0, len(body))
	for _, s := range body {
		if f, ok := s.(ForStmt); ok {
			nb, c, fl := o.constFoldStores(f.Body)
			if c {
				f.Body = nb
				changed = true
			}
			folds += fl
			out = append(out, f)
			continue
		}
		st, ok := s.(StoreStmt)
		if !ok {
			out = append(out, s)
			continue
		}
		if _, already := st.Val.(ConstExpr); already {
			out = append(out, s)
			continue
		}
		if v, ok := constValue(st.Val); ok {
			out = append(out, StoreStmt{Name: st.Name, Idx: st.Idx, Val: ConstExpr{Value: v}})
			changed = true
			folds++
			continue
		}
		out = append(out, s)
	}
	return out, changed, folds
}

// deadStoreElim removes stores to buffers with
// no subsequent load. Conservative: a buffer
// is live if any VarExpr references it, and
// the function output is always live.
func (o *TIROptimizer) deadStoreElim(body []Stmt, outputName string) ([]Stmt, bool) {
	live := map[string]bool{}
	if outputName != "" {
		live[outputName] = true
	}
	var collect func([]Stmt)
	collect = func(stmts []Stmt) {
		for _, s := range stmts {
			switch t := s.(type) {
			case ForStmt:
				collect(t.Body)
			case StoreStmt:
				collectExprs(live, t.Val)
			case AllocateStmt:
				// allocations are neutral
			}
		}
	}
	collect(body)
	changed := false
	out := make([]Stmt, 0, len(body))
	for _, s := range body {
		if st, ok := s.(StoreStmt); ok && !live[st.Name] {
			changed = true
			continue
		}
		out = append(out, s)
	}
	return out, changed
}

// collectExprs marks every referenced buffer.
func collectExprs(live map[string]bool, e Expr) {
	if e == nil {
		return
	}
	switch t := e.(type) {
	case VarExpr:
		live[t.Name] = true
		for _, idx := range t.Idx {
			collectExprs(live, idx)
		}
	case BinaryExpr:
		collectExprs(live, t.Left)
		collectExprs(live, t.Right)
	case CallExpr:
		for _, a := range t.Args {
			collectExprs(live, a)
		}
	case ReduceExpr:
		live[t.Src] = true
		for _, idx := range t.SrcIdx {
			collectExprs(live, idx)
		}
	}
}

// constValue returns the constant value of an
// expression if it is fully constant.
func constValue(e Expr) (float64, bool) {
	switch t := e.(type) {
	case ConstExpr:
		return t.Value, true
	case BinaryExpr:
		l, ok := constValue(t.Left)
		if !ok {
			return 0, false
		}
		r, ok := constValue(t.Right)
		if !ok {
			return 0, false
		}
		switch t.Op {
		case "+":
			return l + r, true
		case "-":
			return l - r, true
		case "*":
			return l * r, true
		case "/":
			if r == 0 {
				return 0, false
			}
			return l / r, true
		case "max":
			if l > r {
				return l, true
			}
			return r, true
		case "min":
			if l < r {
				return l, true
			}
			return r, true
		}
	case CallExpr:
		if len(t.Args) == 1 {
			a, ok := constValue(t.Args[0])
			if !ok {
				return 0, false
			}
			switch t.Op {
			case "exp":
				return expConst(a), true
			case "sqrt":
				if a >= 0 {
					return sqrtConst(a), true
				}
			}
		}
	}
	return 0, false
}
