package compiler

import (
	"testing"

	"github.com/astrovox/astrovox/graph"
)

func TestInterpreter_ScalarOutput(t *testing.T) {
	_ = NewInterpreter()
	m := NewModule()
	m.Add(&Func{Name: "f", Body: []Stmt{}})
	out, err := NewInterpreter().Execute(m, "f", map[string][]float64{})
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if len(out) == 0 {
		t.Fatal("expected non-empty output")
	}
}

func TestInterpreter_MissingFunction(t *testing.T) {
	it := NewInterpreter()
	_, err := it.Execute(NewModule(), "nonexistent", nil)
	if err == nil {
		t.Fatal("expected error for missing function")
	}
}

func TestInterpreter_EmptyModule(t *testing.T) {
	it := NewInterpreter()
	_, err := it.Execute(NewModule(), "f", nil)
	if err == nil {
		t.Fatal("expected error for empty module")
	}
}

func TestInterpreter_AddChain(t *testing.T) {
	_ = NewInterpreter()
	m := NewModule()
	g := graph.New("chain")
	n0 := addNode(g, "c0", 0, 0)
	n1 := addNode(g, "c1", 0, 0)
	n2 := addNode(g, "add", n0, n1)
	m.Add(&Func{Name: "f", Body: []Stmt{}})
	_ = n2
	_ = m
}

func TestLowerer_New(t *testing.T) {
	l := NewLowerer()
	if l == nil {
		t.Fatal("expected non-nil lowerer")
	}
}

func TestLowerer_LowerEmpty(t *testing.T) {
	l := NewLowerer()
	g := graph.New("empty")
	m, err := l.Lower(g)
	if err != nil {
		t.Fatalf("Lower empty: %v", err)
	}
	if m == nil {
		t.Fatal("expected non-nil module")
	}
}

func TestModule_AddAndGet(t *testing.T) {
	m := NewModule()
	f := &Func{Name: "f"}
	m.Add(f)
	got, ok := m.Get("f")
	if !ok || got != f {
		t.Fatal("expected to retrieve added func")
	}
}

func TestModule_GetMissing(t *testing.T) {
	m := NewModule()
	if _, ok := m.Get("missing"); ok {
		t.Fatal("expected false for missing func")
	}
}

func TestModule_MultipleFuncs(t *testing.T) {
	m := NewModule()
	m.Add(&Func{Name: "a"})
	m.Add(&Func{Name: "b"})
	if len(m.Funcs) != 2 {
		t.Fatalf("funcs = %d, want 2", len(m.Funcs))
	}
}

func TestBuffer_Elements(t *testing.T) {
	b := Buffer{Shape: []int{2, 3}}
	if b.Elements() != 6 {
		t.Fatalf("elements = %d, want 6", b.Elements())
	}
}

func TestBuffer_ElementsScalar(t *testing.T) {
	b := Buffer{Shape: []int{}}
	if b.Elements() != 1 {
		t.Fatalf("scalar elements = %d, want 1", b.Elements())
	}
}

func TestDefaultOptions(t *testing.T) {
	opts := DefaultOptions()
	if opts.Target == "" {
		t.Fatal("expected non-empty target in default options")
	}
}

func TestNewCompiler(t *testing.T) {
	c, err := NewCompiler(DefaultOptions())
	if err != nil {
		t.Fatalf("NewCompiler: %v", err)
	}
	if c == nil {
		t.Fatal("expected non-nil compiler")
	}
}

func TestCompilerCompile_EmptyGraph(t *testing.T) {
	c, _ := NewCompiler(DefaultOptions())
	_, err := c.Compile(graph.New("empty"))
	if err == nil {
		t.Fatal("expected error for empty graph")
	}
}

func TestConstValue_Number(t *testing.T) {
	e := ConstExpr{Value: 42}
	v, ok := constValue(e)
	if !ok || v != 42 {
		t.Fatalf("constValue = %v, ok=%v, want 42,true", v, ok)
	}
}

func TestConstValue_VarExpr(t *testing.T) {
	e := VarExpr{Name: "x"}
	_, ok := constValue(e)
	if ok {
		t.Fatal("expected false for variable expr")
	}
}

func TestSanitize(t *testing.T) {
	got := sanitize("hello world")
	if got != "hello_world" {
		t.Fatalf("sanitize = %q, want hello_world", got)
	}
}

func TestIsElementwise(t *testing.T) {
	if !isElementwise("add") {
		t.Error("add should be elementwise")
	}
	if isElementwise("matmul") {
		t.Error("matmul should not be elementwise")
	}
}

func TestIsReduction(t *testing.T) {
	if !isReduction("sum") {
		t.Error("sum should be reduction")
	}
	if isReduction("add") {
		t.Error("add should not be reduction")
	}
}

func TestFlatIndex(t *testing.T) {
	idx, err := flatIndex([]int{1, 2}, []int{3, 4}, 12)
	if err != nil {
		t.Fatalf("flatIndex: %v", err)
	}
	if idx != 6 {
		t.Fatalf("flatIndex = %d, want 6", idx)
	}
}

func TestTIROptimizer_New(t *testing.T) {
	o := NewTIROptimizer()
	if o == nil {
		t.Fatal("expected non-nil optimizer")
	}
}

func TestTIROptimizer_OptimizeEmpty(t *testing.T) {
	o := NewTIROptimizer()
	m := NewModule()
	_, _, _, err := o.Optimize(m)
	if err != nil {
		t.Fatalf("Optimize empty: %v", err)
	}
}

func TestBuildTwoSourceGraph(t *testing.T) {
	g, n0, n1, n2 := buildTwoSourceGraph(t)
	if g == nil {
		t.Fatal("expected non-nil graph")
	}
	if n0 == n1 || n0 == n2 || n1 == n2 {
		t.Fatal("expected distinct node ids")
	}
}
