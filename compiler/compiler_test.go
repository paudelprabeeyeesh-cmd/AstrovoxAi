package compiler

import (
	"math"
	"testing"

	"github.com/astrovox/astrovox/graph"
	"github.com/astrovox/astrovox/tensor"
)

// fixedShape returns a shape fn yielding a
// constant shape regardless of inputs (for
// source nodes).
func fixedShape(dims ...int) func([]tensor.Shape) ([]tensor.Shape, error) {
	return func([]tensor.Shape) ([]tensor.Shape, error) {
		return []tensor.Shape{tensor.MustShape(dims...)}, nil
	}
}

// sameShape returns a shape fn propagating
// the first input's shape.
func sameShape(inputs []tensor.Shape) ([]tensor.Shape, error) {
	if len(inputs) == 0 {
		return nil, errNoInputs
	}
	return []tensor.Shape{inputs[0]}, nil
}

var errNoInputs = &shapeError{}

type shapeError struct{}

func (*shapeError) Error() string { return "no inputs" }

// elemFn builds a forward fn applying an
// elementwise scalar function.
func elemFn(fn func(float64) float64) func([]*tensor.Tensor) ([]*tensor.Tensor, error) {
	return func(inputs []*tensor.Tensor) ([]*tensor.Tensor, error) {
		src := inputs[0].Float64()
		out, err := tensor.New(inputs[0].DType(), inputs[0].Shape().Dims())
		if err != nil {
			return nil, err
		}
		dst := out.Float64()
		for i, v := range src {
			dst[i] = fn(v)
		}
		return []*tensor.Tensor{out}, nil
	}
}

// add node helper.
func addNode(g *graph.Graph, name string, from1, from2 int) int {
	id, err := g.AddNode(graph.OpFunc{
		OpName:   name,
		ShapeFn:  sameShape,
		ForwardFn: elemFn(func(float64) float64 { return 0 }),
	}, nil)
	if err != nil {
		panic(err)
	}
	return id
}

// buildTwoSourceGraph builds:
//   n0 = source [2,2]
//   n1 = source [2,2]
//   n2 = add(n0, n1)
//   n3 = relu(n2)   (sink)
func buildTwoSourceGraph(t *testing.T) (*graph.Graph, int, int, int) {
	t.Helper()
	g := graph.New("test")
	n0, err := g.AddNode(graph.OpFunc{
		OpName:  "src0",
		ShapeFn: fixedShape(2, 2),
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	n1, err := g.AddNode(graph.OpFunc{
		OpName:  "src1",
		ShapeFn: fixedShape(2, 2),
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	n2, err := g.AddNode(graph.OpFunc{
		OpName:  "add",
		ShapeFn: sameShape,
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	n3, err := g.AddNode(graph.OpFunc{
		OpName:  "relu",
		ShapeFn: sameShape,
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := g.AddEdge(n0, n2, 0, 0); err != nil {
		t.Fatal(err)
	}
	if _, err := g.AddEdge(n1, n2, 0, 1); err != nil {
		t.Fatal(err)
	}
	if _, err := g.AddEdge(n2, n3, 0, 0); err != nil {
		t.Fatal(err)
	}
	if err := g.MarkOutput(n3); err != nil {
		t.Fatal(err)
	}
	return g, n0, n1, n3
}

func TestLowerSingle(t *testing.T) {
	g, n0, n1, _ := buildTwoSourceGraph(t)
	low := NewLowerer()
	fn, err := low.LowerSingle(g)
	if err != nil {
		t.Fatal(err)
	}
	if fn.Name != "main" {
		t.Fatalf("name = %q, want main", fn.Name)
	}
	if len(fn.Params) != 2 {
		t.Fatalf("params = %d, want 2", len(fn.Params))
	}
	if fn.Params[0].Name != "input_"+itoa(n0) ||
		fn.Params[1].Name != "input_"+itoa(n1) {
		t.Fatalf("param names = %v, %v", fn.Params[0].Name, fn.Params[1].Name)
	}
	if fn.Output.Shape[0] != 2 || fn.Output.Shape[1] != 2 {
		t.Fatalf("output shape = %v, want [2 2]", fn.Output.Shape)
	}
	if len(fn.Body) == 0 {
		t.Fatal("empty body")
	}
}

func itoa(i int) string {
	if i == 0 {
		return "0"
	}
	var digits []byte
	for i > 0 {
		digits = append([]byte{byte('0' + i%10)}, digits...)
		i /= 10
	}
	return string(digits)
}

func TestCompilerCompile(t *testing.T) {
	g, _, _, _ := buildTwoSourceGraph(t)
	c, err := NewCompiler(DefaultOptions())
	if err != nil {
		t.Fatal(err)
	}
	res, err := c.Compile(g)
	if err != nil {
		t.Fatal(err)
	}
	if res.Stats.Funcs != 1 {
		t.Fatalf("funcs = %d, want 1", res.Stats.Funcs)
	}
	if res.Stats.Stmts == 0 {
		t.Fatal("no statements")
	}
	f, ok := res.Module.Get("main")
	if !ok {
		t.Fatal("main function missing")
	}
	if len(f.Params) != 2 {
		t.Fatalf("params = %d, want 2", len(f.Params))
	}
}

func TestCompilerBadTarget(t *testing.T) {
	if _, err := NewCompiler(Options{Target: "sparc"}); err == nil {
		t.Fatal("expected target error")
	}
}

func TestInterpreterAddRelu(t *testing.T) {
	g, n0, n1, _ := buildTwoSourceGraph(t)
	c, _ := NewCompiler(DefaultOptions())
	res, err := c.Compile(g)
	if err != nil {
		t.Fatal(err)
	}
	interp := NewInterpreter()
	// x0 = [[1,-2],[3,-4]], x1 = [[-1,2],[-3,4]]
	// add = [[0,0],[0,0]], relu(add) = [[0,0],[0,0]]
	x0 := []float64{1, -2, 3, -4}
	x1 := []float64{-1, 2, -3, 4}
	f, _ := res.Module.Get("main")
	params := map[string][]float64{
		f.Params[0].Name: x0,
		f.Params[1].Name: x1,
	}
	out, err := interp.Execute(res.Module, "main", params)
	if err != nil {
		t.Fatal(err)
	}
	got := out[f.Output.Name]
	for i, v := range got {
		if v != 0 {
			t.Fatalf("out[%d] = %v, want 0", i, v)
		}
	}
	_ = n0
	_ = n1
}

func TestInterpreterMatMul(t *testing.T) {
	// y = x0 @ x1 with x0=[[1,2],[3,4]], x1=[[5,6],[7,8]]
	// y = [[19,22],[43,50]]
	g := graph.New("matmul")
	n0, _ := g.AddNode(graph.OpFunc{
		OpName:  "src0",
		ShapeFn: fixedShape(2, 2),
	}, nil)
	n1, _ := g.AddNode(graph.OpFunc{
		OpName:  "src1",
		ShapeFn: fixedShape(2, 2),
	}, nil)
	n2, _ := g.AddNode(graph.OpFunc{
		OpName:  "matmul",
		ShapeFn: func(inputs []tensor.Shape) ([]tensor.Shape, error) {
			return []tensor.Shape{tensor.MustShape(2, 2)}, nil
		},
	}, nil)
	if _, err := g.AddEdge(n0, n2, 0, 0); err != nil {
		t.Fatal(err)
	}
	if _, err := g.AddEdge(n1, n2, 0, 1); err != nil {
		t.Fatal(err)
	}
	if err := g.MarkOutput(n2); err != nil {
		t.Fatal(err)
	}
	c, _ := NewCompiler(DefaultOptions())
	res, err := c.Compile(g)
	if err != nil {
		t.Fatal(err)
	}
	interp := NewInterpreter()
	f, _ := res.Module.Get("main")
	params := map[string][]float64{
		f.Params[0].Name: {1, 2, 3, 4},
		f.Params[1].Name: {5, 6, 7, 8},
	}
	out, err := interp.Execute(res.Module, "main", params)
	if err != nil {
		t.Fatal(err)
	}
	got := out[f.Output.Name]
	want := []float64{19, 22, 43, 50}
	for i, v := range got {
		if v != want[i] {
			t.Fatalf("out[%d] = %v, want %v", i, v, want[i])
		}
	}
}

func TestInterpreterSumReduction(t *testing.T) {
	// y = sum(x, axis=1) with x = [[1,2,3],[4,5,6]]
	// y = [6, 15]
	g := graph.New("sum")
	n0, _ := g.AddNode(graph.OpFunc{
		OpName:  "src0",
		ShapeFn: fixedShape(2, 3),
	}, nil)
	n1, _ := g.AddNode(graph.OpFunc{
		OpName:  "sum",
		ShapeFn: func(inputs []tensor.Shape) ([]tensor.Shape, error) {
			return []tensor.Shape{tensor.MustShape(2)}, nil
		},
	}, nil)
	if _, err := g.AddEdge(n0, n1, 0, 0); err != nil {
		t.Fatal(err)
	}
	if err := g.MarkOutput(n1); err != nil {
		t.Fatal(err)
	}
	c, _ := NewCompiler(DefaultOptions())
	res, err := c.Compile(g)
	if err != nil {
		t.Fatal(err)
	}
	interp := NewInterpreter()
	f, _ := res.Module.Get("main")
	params := map[string][]float64{
		f.Params[0].Name: {1, 2, 3, 4, 5, 6},
	}
	out, err := interp.Execute(res.Module, "main", params)
	if err != nil {
		t.Fatal(err)
	}
	got := out[f.Output.Name]
	want := []float64{6, 15}
	for i, v := range got {
		if v != want[i] {
			t.Fatalf("out[%d] = %v, want %v", i, v, want[i])
		}
	}
}

func TestInterpreterIterationBound(t *testing.T) {
	g, _, _, _ := buildTwoSourceGraph(t)
	c, _ := NewCompiler(DefaultOptions())
	res, _ := c.Compile(g)
	interp := NewInterpreter()
	interp.MaxIters = 2
	f, _ := res.Module.Get("main")
	params := map[string][]float64{
		f.Params[0].Name: {1, 2, 3, 4},
		f.Params[1].Name: {1, 2, 3, 4},
	}
	if _, err := interp.Execute(res.Module, "main", params); err == nil {
		t.Fatal("expected iteration bound error")
	}
}

func TestInterpreterMissingParam(t *testing.T) {
	g, _, _, _ := buildTwoSourceGraph(t)
	c, _ := NewCompiler(DefaultOptions())
	res, _ := c.Compile(g)
	interp := NewInterpreter()
	f, _ := res.Module.Get("main")
	params := map[string][]float64{
		f.Params[0].Name: {1, 2, 3, 4},
	}
	if _, err := interp.Execute(res.Module, "main", params); err == nil {
		t.Fatal("expected missing parameter error")
	}
}

func TestInterpreterParamLengthMismatch(t *testing.T) {
	g, _, _, _ := buildTwoSourceGraph(t)
	c, _ := NewCompiler(DefaultOptions())
	res, _ := c.Compile(g)
	interp := NewInterpreter()
	f, _ := res.Module.Get("main")
	params := map[string][]float64{
		f.Params[0].Name: {1, 2},
		f.Params[1].Name: {1, 2, 3, 4},
	}
	if _, err := interp.Execute(res.Module, "main", params); err == nil {
		t.Fatal("expected length mismatch error")
	}
}

func TestTIROptimizerConstFold(t *testing.T) {
	// Build a module with a constant store
	// and verify folding.
	m := NewModule()
	out := Buffer{Name: "out", Shape: []int{1}, DType: "float64"}
	body := []Stmt{
		AllocateStmt{Buffer: out},
		StoreStmt{
			Name: "out",
			Idx:  []Expr{ConstExpr{Value: 0}},
			Val: BinaryExpr{
				Op:    "+",
				Left:  ConstExpr{Value: 2},
				Right: ConstExpr{Value: 3},
			},
		},
	}
	m.Add(&Func{Name: "main", Output: out, Body: body})
	opt := NewTIROptimizer()
	mod, passes, folds, err := opt.Optimize(m)
	if err != nil {
		t.Fatal(err)
	}
	if folds != 1 {
		t.Fatalf("folds = %d, want 1", folds)
	}
	if passes == 0 {
		t.Fatal("no passes run")
	}
	f := mod.Funcs["main"]
	store := f.Body[1].(StoreStmt)
	c, ok := store.Val.(ConstExpr)
	if !ok {
		t.Fatalf("store value not folded: %T", store.Val)
	}
	if c.Value != 5 {
		t.Fatalf("folded value = %v, want 5", c.Value)
	}
}

func TestTIROptimizerDeadStore(t *testing.T) {
	// A store to a buffer that is never
	// loaded must be eliminated.
	m := NewModule()
	dead := Buffer{Name: "dead", Shape: []int{1}, DType: "float64"}
	live := Buffer{Name: "live", Shape: []int{1}, DType: "float64"}
	body := []Stmt{
		AllocateStmt{Buffer: dead},
		AllocateStmt{Buffer: live},
		StoreStmt{Name: "dead", Idx: []Expr{ConstExpr{Value: 0}}, Val: ConstExpr{Value: 1}},
		StoreStmt{
			Name: "live",
			Idx:  []Expr{ConstExpr{Value: 0}},
			Val: VarExpr{Name: "live", Idx: []Expr{ConstExpr{Value: 0}}},
		},
	}
	m.Add(&Func{Name: "main", Output: live, Body: body})
	opt := NewTIROptimizer()
	mod, _, _, err := opt.Optimize(m)
	if err != nil {
		t.Fatal(err)
	}
	f := mod.Funcs["main"]
	if len(f.Body) != 3 {
		t.Fatalf("body length = %d, want 3 (dead store removed)", len(f.Body))
	}
	for _, s := range f.Body {
		if st, ok := s.(StoreStmt); ok && st.Name == "dead" {
			t.Fatal("dead store survived")
		}
	}
}

func TestConstValue(t *testing.T) {
	e := BinaryExpr{
		Op:    "*",
		Left:  BinaryExpr{Op: "+", Left: ConstExpr{Value: 1}, Right: ConstExpr{Value: 2}},
		Right: ConstExpr{Value: 4},
	}
	v, ok := constValue(e)
	if !ok {
		t.Fatal("expected constant")
	}
	if v != 12 {
		t.Fatalf("value = %v, want 12", v)
	}
	// Division by zero must not fold.
	e = BinaryExpr{Op: "/", Left: ConstExpr{Value: 1}, Right: ConstExpr{Value: 0}}
	if _, ok := constValue(e); ok {
		t.Fatal("expected division by zero to not fold")
	}
	// Non-constant expression must not fold.
	e = BinaryExpr{Op: "+", Left: ConstExpr{Value: 1}, Right: VarExpr{Name: "x"}}
	if _, ok := constValue(e); ok {
		t.Fatal("expected non-constant to not fold")
	}
}

func TestInterpreterExpCall(t *testing.T) {
	m := NewModule()
	out := Buffer{Name: "out", Shape: []int{1}, DType: "float64"}
	body := []Stmt{
		AllocateStmt{Buffer: out},
		StoreStmt{
			Name: "out",
			Idx:  []Expr{ConstExpr{Value: 0}},
			Val:  CallExpr{Op: "exp", Args: []Expr{ConstExpr{Value: 0}}},
		},
	}
	m.Add(&Func{Name: "main", Output: out, Body: body})
	interp := NewInterpreter()
	res, err := interp.Execute(m, "main", nil)
	if err != nil {
		t.Fatal(err)
	}
	got := res["out"][0]
	if math.Abs(got-1) > 1e-9 {
		t.Fatalf("exp(0) = %v, want 1", got)
	}
}
