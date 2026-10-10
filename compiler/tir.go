// Package compiler implements the Astrovox JIT
// compilation pipeline: lowering computational
// graphs to the Tensor IR (TIR), TIR-level
// optimizations, and backend code generation
// with an AST interpreter as the reference
// backend.
package compiler

// Stmt is a TIR statement.
type Stmt interface{ stmtNode() }

// Expr is a TIR expression.
type Expr interface{ exprNode() }

// --- Expressions ---

// VarExpr references a buffer element.
type VarExpr struct {
	Name string
	Idx  []Expr
}

func (VarExpr) exprNode() {}

// ConstExpr is a literal constant.
type ConstExpr struct {
	Value float64
}

func (ConstExpr) exprNode() {}

// BinaryExpr applies an operator to two exprs.
type BinaryExpr struct {
	Op    string // "+", "-", "*", "/", "max", "min"
	Left  Expr
	Right Expr
}

func (BinaryExpr) exprNode() {}

// CallExpr invokes a primitive.
type CallExpr struct {
	Op   string // "exp", "log", "sqrt", "tanh", "relu", "sigmoid"
	Args []Expr
}

func (CallExpr) exprNode() {}

// ReduceExpr folds a buffer over axes.
type ReduceExpr struct {
	Op     string // "sum", "prod", "max", "min"
	Src    string
	SrcIdx []Expr // index expressions with loop vars
	Axes   []int  // loop-variable positions being reduced
	Init   float64
}

func (ReduceExpr) exprNode() {}

// --- Statements ---

// AllocateStmt declares an output buffer.
type AllocateStmt struct {
	Buffer Buffer
}

func (AllocateStmt) stmtNode() {}

// StoreStmt writes an expression into a buffer
// element.
type StoreStmt struct {
	Name string
	Idx  []Expr
	Val  Expr
}

func (StoreStmt) stmtNode() {}

// ForStmt is a bounded loop over one axis.
type ForStmt struct {
	Var   string
	Start int
	End   Expr // nil means bound by buffer dim
	Body  []Stmt
}

func (ForStmt) stmtNode() {}

// LetStmt binds an expression to a name.
type LetStmt struct {
	Name string
	Val  Expr
}

func (LetStmt) stmtNode() {}

// ReturnStmt yields the function result.
type ReturnStmt struct {
	Names []string
}

func (ReturnStmt) stmtNode() {}

// Buffer describes a TIR tensor allocation.
type Buffer struct {
	Name  string
	Shape []int
	DType string
}

// Elements returns the element count.
func (b Buffer) Elements() int {
	n := 1
	for _, d := range b.Shape {
		n *= d
	}
	return n
}

// Func is a compiled TIR function.
type Func struct {
	Name   string
	Params []Buffer
	Output Buffer
	Body   []Stmt
	Source string // originating op name
}

// Module is a collection of TIR functions.
type Module struct {
	Funcs map[string]*Func
	Order []string
}

// NewModule creates an empty module.
func NewModule() *Module {
	return &Module{Funcs: map[string]*Func{}}
}

// Add registers a function in the module.
func (m *Module) Add(f *Func) {
	if _, ok := m.Funcs[f.Name]; !ok {
		m.Order = append(m.Order, f.Name)
	}
	m.Funcs[f.Name] = f
}

// Get returns a function by name.
func (m *Module) Get(name string) (*Func, bool) {
	f, ok := m.Funcs[name]
	return f, ok
}
