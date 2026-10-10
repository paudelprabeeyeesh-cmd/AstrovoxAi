package lang

import (
	"fmt"
	"strings"
)

// Optimizer performs AST-level optimizations.
type Optimizer struct {
	passes []OptPass
	stats  OptStats
}

// OptStats tracks optimization statistics.
type OptStats struct {
	ConstantsFolded   int
	IdentitiesRemoved int
	DeadCodeRemoved   int
	InlinedFunctions  int
}

// OptPass is an optimization pass over a file.
type OptPass interface {
	Name() string
	Run(f *File) *File
}

// NewOptimizer creates an optimizer with default passes.
func NewOptimizer() *Optimizer {
	return &Optimizer{
		passes: []OptPass{
			&ConstantFoldingPass{},
			&AlgebraicIdentityPass{},
			&DeadCodeEliminationPass{},
			&StrengthReductionPass{},
		},
	}
}

// Optimize runs all passes on a file.
func (o *Optimizer) Optimize(f *File) *File {
	for _, pass := range o.passes {
		f = pass.Run(f)
	}
	return f
}

// ConstantFoldingPass folds constant expressions.
type ConstantFoldingPass struct{}

func (p *ConstantFoldingPass) Name() string { return "const-fold" }

func (p *ConstantFoldingPass) Run(f *File) *File {
	fo := &folder{}
	for _, d := range f.Decls {
		fn, ok := d.(*FuncDecl)
		if !ok {
			continue
		}
		fn.Body = foldStmts(fn.Body, fo)
	}
	return f
}

// foldConstants folds constant sub-expressions.
type folder struct{ folded int }

func (fo *folder) fold(e Expr) Expr {
	switch e := e.(type) {
	case *BinaryExpr:
		e.Left = fo.fold(e.Left)
		e.Right = fo.fold(e.Right)
		if l, ok := e.Left.(*IntLit); ok {
			if r, ok := e.Right.(*IntLit); ok {
				switch e.Op {
				case "+":
					fo.folded++
					return &IntLit{Value: l.Value + r.Value, Line: e.Line, Col: e.Col}
				case "-":
					fo.folded++
					return &IntLit{Value: l.Value - r.Value, Line: e.Line, Col: e.Col}
				case "*":
					fo.folded++
					return &IntLit{Value: l.Value * r.Value, Line: e.Line, Col: e.Col}
				case "/":
					if r.Value != 0 {
						fo.folded++
						return &IntLit{Value: l.Value / r.Value, Line: e.Line, Col: e.Col}
					}
				case "%":
					if r.Value != 0 {
						fo.folded++
						return &IntLit{Value: l.Value % r.Value, Line: e.Line, Col: e.Col}
					}
				case "<":
					fo.folded++
					return &BoolLit{Value: l.Value < r.Value, Line: e.Line, Col: e.Col}
				case ">":
					fo.folded++
					return &BoolLit{Value: l.Value > r.Value, Line: e.Line, Col: e.Col}
				case "<=":
					fo.folded++
					return &BoolLit{Value: l.Value <= r.Value, Line: e.Line, Col: e.Col}
				case ">=":
					fo.folded++
					return &BoolLit{Value: l.Value >= r.Value, Line: e.Line, Col: e.Col}
				case "==":
					fo.folded++
					return &BoolLit{Value: l.Value == r.Value, Line: e.Line, Col: e.Col}
				case "!=":
					fo.folded++
					return &BoolLit{Value: l.Value != r.Value, Line: e.Line, Col: e.Col}
				}
			}
		}
		return e
	case *UnaryExpr:
		e.Expr = fo.fold(e.Expr)
		if l, ok := e.Expr.(*IntLit); ok {
			switch e.Op {
			case "-":
				fo.folded++
				return &IntLit{Value: -l.Value, Line: e.Line, Col: e.Col}
			}
		}
		return e
	case *CallExpr:
		e.Args = fo.foldList(e.Args)
		return e
	case *IndexExpr:
		e.Object = fo.fold(e.Object)
		e.Index = fo.fold(e.Index)
		return e
	case *FieldExpr:
		e.Object = fo.fold(e.Object)
		return e
	case *MethodExpr:
		e.Object = fo.fold(e.Object)
		e.Args = fo.foldList(e.Args)
		return e
	}
	return e
}

func (fo *folder) foldList(list []Expr) []Expr {
	out := make([]Expr, len(list))
	for i, e := range list {
		out[i] = fo.fold(e)
	}
	return out
}

func foldStmts(stmts []Stmt, fo *folder) []Stmt {
	for _, s := range stmts {
		switch s := s.(type) {
		case *LetStmt:
			s.Value = fo.fold(s.Value)
		case *AssignStmt:
			s.Value = fo.fold(s.Value)
		case *ReturnStmt:
			if s.Value != nil {
				s.Value = fo.fold(s.Value)
			}
		case *ExprStmt:
			s.X = fo.fold(s.X)
		case *IfStmt:
			s.Cond = fo.fold(s.Cond)
			foldStmts(s.Then, fo)
			foldStmts(s.Else, fo)
		case *WhileStmt:
			s.Cond = fo.fold(s.Cond)
			foldStmts(s.Body, fo)
		case *ForStmt:
			s.Iter = fo.fold(s.Iter)
			foldStmts(s.Body, fo)
		case *BlockStmt:
			foldStmts(s.Stmts, fo)
		}
	}
	return stmts
}

// AlgebraicIdentityPass removes algebraic identities (x+0, x*1, etc.).
type AlgebraicIdentityPass struct{}

func (p *AlgebraicIdentityPass) Name() string { return "algebraic-identity" }

func (p *AlgebraicIdentityPass) Run(f *File) *File {
	for _, d := range f.Decls {
		if fn, ok := d.(*FuncDecl); ok {
			simplifyStmts(fn.Body)
		}
	}
	return f
}

func simplifyStmts(stmts []Stmt) {
	for _, s := range stmts {
		switch s := s.(type) {
		case *LetStmt:
			s.Value = simplify(s.Value)
		case *AssignStmt:
			s.Value = simplify(s.Value)
		case *ReturnStmt:
			if s.Value != nil {
				s.Value = simplify(s.Value)
			}
		case *ExprStmt:
			s.X = simplify(s.X)
		case *IfStmt:
			s.Cond = simplify(s.Cond)
			simplifyStmts(s.Then)
			simplifyStmts(s.Else)
		case *WhileStmt:
			s.Cond = simplify(s.Cond)
			simplifyStmts(s.Body)
		case *ForStmt:
			simplifyStmts(s.Body)
		}
	}
}

func simplify(e Expr) Expr {
	b, ok := e.(*BinaryExpr)
	if !ok {
		return e
	}
	b.Left = simplify(b.Left)
	b.Right = simplify(b.Right)

	isZero := func(e Expr) bool {
		if l, ok := e.(*IntLit); ok {
			return l.Value == 0
		}
		return false
	}
	isOne := func(e Expr) bool {
		if l, ok := e.(*IntLit); ok {
			return l.Value == 1
		}
		return false
	}

	switch b.Op {
	case "+":
		if isZero(b.Right) {
			return b.Left
		}
		if isZero(b.Left) {
			return b.Right
		}
	case "-":
		if isZero(b.Right) {
			return b.Left
		}
	case "*":
		if isOne(b.Right) {
			return b.Left
		}
		if isOne(b.Left) {
			return b.Right
		}
		if isZero(b.Left) || isZero(b.Right) {
			return &IntLit{Value: 0, Line: b.Line, Col: b.Col}
		}
	case "/":
		if isOne(b.Right) {
			return b.Left
		}
	}
	return b
}

// DeadCodeEliminationPass removes unreachable code.
type DeadCodeEliminationPass struct{}

func (p *DeadCodeEliminationPass) Name() string { return "dead-code" }

func (p *DeadCodeEliminationPass) Run(f *File) *File {
	for _, d := range f.Decls {
		if fn, ok := d.(*FuncDecl); ok {
			fn.Body = eliminateDeadCode(fn.Body)
		}
	}
	return f
}

func eliminateDeadCode(stmts []Stmt) []Stmt {
	out := []Stmt{}
	for _, s := range stmts {
		out = append(out, s)
		if _, isReturn := s.(*ReturnStmt); isReturn {
			break
		}
	}
	return out
}

// StrengthReductionPass replaces expensive ops with cheaper ones.
type StrengthReductionPass struct{}

func (p *StrengthReductionPass) Name() string { return "strength-reduce" }

func (p *StrengthReductionPass) Run(f *File) *File {
	for _, d := range f.Decls {
		if fn, ok := d.(*FuncDecl); ok {
			applyStrengthReduction(fn.Body)
		}
	}
	return f
}

func applyStrengthReduction(stmts []Stmt) {
	for _, s := range stmts {
		switch s := s.(type) {
		case *LetStmt:
			s.Value = reduce(s.Value)
		case *AssignStmt:
			s.Value = reduce(s.Value)
		case *ReturnStmt:
			if s.Value != nil {
				s.Value = reduce(s.Value)
			}
		case *ExprStmt:
			s.X = reduce(s.X)
		case *IfStmt:
			applyStrengthReduction(s.Then)
			applyStrengthReduction(s.Else)
		case *WhileStmt:
			applyStrengthReduction(s.Body)
		case *ForStmt:
			applyStrengthReduction(s.Body)
		}
	}
}

func reduce(e Expr) Expr {
	b, ok := e.(*BinaryExpr)
	if !ok {
		return e
	}
	reduce(b.Left)
	reduce(b.Right)
	// x * 2 -> x + x, x * 4 -> (x + x) + (x + x)
	if l, ok := b.Right.(*IntLit); ok && b.Op == "*" {
		if l.Value == 2 {
			return &BinaryExpr{Op: "+", Left: b.Left, Right: b.Left, Line: b.Line, Col: b.Col}
		}
		if l.Value == 4 {
			x2 := &BinaryExpr{Op: "+", Left: b.Left, Right: b.Left, Line: b.Line, Col: b.Col}
			return &BinaryExpr{Op: "+", Left: x2, Right: x2, Line: b.Line, Col: b.Col}
		}
	}
	// x / 2^n handled by client
	return b
}

// SSAOptimizer converts to SSA-like form for further optimization.
type SSAOptimizer struct {
	varCounter map[string]int
	versions   map[string]int
}

// NewSSAOptimizer creates an SSA optimizer.
func NewSSAOptimizer() *SSAOptimizer {
	return &SSAOptimizer{
		varCounter: make(map[string]int),
		versions:   make(map[string]int),
	}
}

// Rename renames variables to unique versions (SSA form).
func (s *SSAOptimizer) Rename(stmts []Stmt) []Stmt {
	for _, st := range stmts {
		if let, ok := st.(*LetStmt); ok {
			if v, ok := s.versions[let.Name]; ok {
				s.versions[let.Name] = v + 1
			}
			s.versions[let.Name] = s.versions[let.Name] + 1
		}
	}
	return stmts
}

// Inliner inlines small functions.
type Inliner struct {
	maxSize int
}

// NewInliner creates an inliner with a size threshold.
func NewInliner(maxSize int) *Inliner {
	return &Inliner{maxSize: maxSize}
}

// ShouldInline returns whether a function should be inlined.
func (in *Inliner) ShouldInline(fn *FuncDecl) bool {
	return len(fn.Body) <= in.maxSize
}

// Inline inlines function calls (simplified: returns call unchanged).
func (in *Inliner) Inline(call *CallExpr, fn *FuncDecl) Expr {
	// Full implementation would substitute arguments
	return call
}

// Generate produces formatted output for the AST (debugging).
func (f *File) Generate() string {
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("// File: %s\n", f.Path))
	for _, d := range f.Decls {
		sb.WriteString(d.String())
		sb.WriteString("\n")
	}
	return sb.String()
}
