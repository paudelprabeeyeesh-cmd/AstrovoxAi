package lang

import (
	"strings"
	"testing"
)

func lex(src string) ([]Token, error) {
	return NewLexer(src).Lex()
}

func parse(src string) (*File, error) {
	tokens, err := lex(src)
	if err != nil {
		return nil, err
	}
	return NewParser(tokens).Parse()
}

func TestLexerIntegers(t *testing.T) {
	toks, err := lex("42 100 0xFF")
	if err != nil {
		t.Fatal(err)
	}
	found := 0
	for _, tk := range toks {
		if tk.Type == TokenInt {
			found++
		}
	}
	if found != 3 {
		t.Errorf("expected 3 int tokens, got %d", found)
	}
}

func TestLexerFloats(t *testing.T) {
	toks, err := lex("3.14 1.0 2.5e3")
	if err != nil {
		t.Fatal(err)
	}
	found := 0
	for _, tk := range toks {
		if tk.Type == TokenFloat {
			found++
		}
	}
	if found != 3 {
		t.Errorf("expected 3 float tokens, got %d", found)
	}
}

func TestLexerStrings(t *testing.T) {
	toks, err := lex(`"hello" "world"`)
	if err != nil {
		t.Fatal(err)
	}
	found := 0
	for _, tk := range toks {
		if tk.Type == TokenString {
			found++
		}
	}
	if found != 2 {
		t.Errorf("expected 2 string tokens, got %d", found)
	}
}

func TestLexerKeywords(t *testing.T) {
	toks, err := lex("fn let mut if else while for return struct")
	if err != nil {
		t.Fatal(err)
	}
	found := 0
	for _, tk := range toks {
		if tk.Type == TokenKeyword {
			found++
		}
	}
	if found != 9 {
		t.Errorf("expected 9 keyword tokens, got %d", found)
	}
}

func TestLexerOperators(t *testing.T) {
	toks, err := lex("+ - * / == != <= >= && || ->")
	if err != nil {
		t.Fatal(err)
	}
	found := 0
	for _, tk := range toks {
		if tk.Type == TokenOperator {
			found++
		}
	}
	if found != 11 {
		t.Errorf("expected 11 operator tokens, got %d", found)
	}
}

func TestLexerComments(t *testing.T) {
	toks, err := lex("// this is a comment\n42 /* block */ 99")
	if err != nil {
		t.Fatal(err)
	}
	comments := 0
	ints := 0
	for _, tk := range toks {
		if tk.Type == TokenComment {
			comments++
		}
		if tk.Type == TokenInt {
			ints++
		}
	}
	if comments != 2 {
		t.Errorf("expected 2 comments, got %d", comments)
	}
	if ints != 2 {
		t.Errorf("expected 2 ints, got %d", ints)
	}
}

func TestLexerStringEscapes(t *testing.T) {
	toks, err := lex(`"a\nb\tc\"d"`)
	if err != nil {
		t.Fatal(err)
	}
	for _, tk := range toks {
		if tk.Type == TokenString {
			want := "a\nb\tc\"d"
			if tk.Value != want {
				t.Errorf("got %q, want %q", tk.Value, want)
			}
		}
	}
}

func TestLexerDelimiters(t *testing.T) {
	toks, err := lex("()[]{},;")
	if err != nil {
		t.Fatal(err)
	}
	found := 0
	for _, tk := range toks {
		if tk.Type == TokenDelimiter {
			found++
		}
	}
	if found != 8 {
		t.Errorf("expected 8 delimiters, got %d", found)
	}
}

func TestLexerUnexpectedChar(t *testing.T) {
	_, err := lex("#$%")
	if err == nil {
		t.Error("expected lexer error for unexpected characters")
	}
}

func TestParserSimpleFunction(t *testing.T) {
	f, err := parse(`fn main() { return 42 }`)
	if err != nil {
		t.Fatal(err)
	}
	if len(f.Decls) != 1 {
		t.Fatalf("expected 1 decl, got %d", len(f.Decls))
	}
	fn, ok := f.Decls[0].(*FuncDecl)
	if !ok {
		t.Fatal("expected FuncDecl")
	}
	if fn.Name != "main" {
		t.Errorf("expected main, got %s", fn.Name)
	}
}

func TestParserLetAndReturn(t *testing.T) {
	f, err := parse(`fn test() { let x = 5; return x }`)
	if err != nil {
		t.Fatal(err)
	}
	fn := f.Decls[0].(*FuncDecl)
	if len(fn.Body) != 2 {
		t.Fatalf("expected 2 stmts, got %d", len(fn.Body))
	}
	if _, ok := fn.Body[0].(*LetStmt); !ok {
		t.Error("expected LetStmt")
	}
	if _, ok := fn.Body[1].(*ReturnStmt); !ok {
		t.Error("expected ReturnStmt")
	}
}

func TestParserBinaryExpr(t *testing.T) {
	f, err := parse(`fn main() { return 1 + 2 * 3 }`)
	if err != nil {
		t.Fatal(err)
	}
	fn := f.Decls[0].(*FuncDecl)
	ret := fn.Body[0].(*ReturnStmt)
	bin, ok := ret.Value.(*BinaryExpr)
	if !ok {
		t.Fatal("expected BinaryExpr")
	}
	if bin.Op != "+" {
		t.Errorf("expected + at root (precedence), got %s", bin.Op)
	}
}

func TestParserUnaryExpr(t *testing.T) {
	f, err := parse(`fn main() { return -5 }`)
	if err != nil {
		t.Fatal(err)
	}
	fn := f.Decls[0].(*FuncDecl)
	ret := fn.Body[0].(*ReturnStmt)
	if _, ok := ret.Value.(*UnaryExpr); !ok {
		t.Error("expected UnaryExpr")
	}
}

func TestParserIfElse(t *testing.T) {
	f, err := parse(`fn main() { if x > 0 { return 1 } else { return 0 } }`)
	if err != nil {
		t.Fatal(err)
	}
	fn := f.Decls[0].(*FuncDecl)
	if _, ok := fn.Body[0].(*IfStmt); !ok {
		t.Error("expected IfStmt")
	}
}

func TestParserWhileLoop(t *testing.T) {
	f, err := parse(`fn main() { while i < 10 { i = i + 1 } }`)
	if err != nil {
		t.Fatal(err)
	}
	fn := f.Decls[0].(*FuncDecl)
	if _, ok := fn.Body[0].(*WhileStmt); !ok {
		t.Error("expected WhileStmt")
	}
}

func TestParserForLoop(t *testing.T) {
	f, err := parse(`fn main() { for i in 0..10 { x = x + i } }`)
	if err != nil {
		t.Fatal(err)
	}
	fn := f.Decls[0].(*FuncDecl)
	if _, ok := fn.Body[0].(*ForStmt); !ok {
		t.Error("expected ForStmt")
	}
}

func TestParserFunctionParams(t *testing.T) {
	f, err := parse(`fn add(a: int, b: int) -> int { return a + b }`)
	if err != nil {
		t.Fatal(err)
	}
	fn := f.Decls[0].(*FuncDecl)
	if len(fn.Params) != 2 {
		t.Fatalf("expected 2 params, got %d", len(fn.Params))
	}
	if fn.Params[0].Name != "a" || fn.Params[1].Name != "b" {
		t.Error("param names wrong")
	}
	if fn.ReturnType == nil || fn.ReturnType.Name != "int" {
		t.Error("expected int return type")
	}
}

func TestParserStructDecl(t *testing.T) {
	f, err := parse(`struct Point { x: int, y: int }`)
	if err != nil {
		t.Fatal(err)
	}
	sd, ok := f.Decls[0].(*StructDecl)
	if !ok {
		t.Fatal("expected StructDecl")
	}
	if sd.Name != "Point" {
		t.Errorf("expected Point, got %s", sd.Name)
	}
	if len(sd.Fields) != 2 {
		t.Errorf("expected 2 fields, got %d", len(sd.Fields))
	}
}

func TestParserEnumDecl(t *testing.T) {
	f, err := parse(`enum Color { Red, Green, Blue }`)
	if err != nil {
		t.Fatal(err)
	}
	ed, ok := f.Decls[0].(*EnumDecl)
	if !ok {
		t.Fatal("expected EnumDecl")
	}
	if len(ed.Variants) != 3 {
		t.Errorf("expected 3 variants, got %d", len(ed.Variants))
	}
}

func TestParserCallExpr(t *testing.T) {
	f, err := parse(`fn main() { let x = foo(1, 2, 3) }`)
	if err != nil {
		t.Fatal(err)
	}
	fn := f.Decls[0].(*FuncDecl)
	let := fn.Body[0].(*LetStmt)
	if _, ok := let.Value.(*CallExpr); !ok {
		t.Error("expected CallExpr")
	}
}

func TestParserMethodCall(t *testing.T) {
	f, err := parse(`fn main() { obj.method() }`)
	if err != nil {
		t.Fatal(err)
	}
	fn := f.Decls[0].(*FuncDecl)
	if _, ok := fn.Body[0].(*ExprStmt); !ok {
		t.Error("expected ExprStmt")
	}
}

func TestParserFieldAccess(t *testing.T) {
	f, err := parse(`fn main() { let x = p.x }`)
	if err != nil {
		t.Fatal(err)
	}
	fn := f.Decls[0].(*FuncDecl)
	let := fn.Body[0].(*LetStmt)
	if _, ok := let.Value.(*FieldExpr); !ok {
		t.Error("expected FieldExpr")
	}
}

func TestParserImport(t *testing.T) {
	f, err := parse(`import "math"`)
	if err != nil {
		t.Fatal(err)
	}
	imp, ok := f.Decls[0].(*ImportDecl)
	if !ok {
		t.Fatal("expected ImportDecl")
	}
	if imp.Path != "math" {
		t.Errorf("expected math, got %s", imp.Path)
	}
}

func TestOptimizerConstantFolding(t *testing.T) {
	f, err := parse(`fn main() { let x = 2 + 3 * 4 }`)
	if err != nil {
		t.Fatal(err)
	}
	opt := NewOptimizer()
	f2 := opt.Optimize(f)
	fn := f2.Decls[0].(*FuncDecl)
	let := fn.Body[0].(*LetStmt)
	if lit, ok := let.Value.(*IntLit); ok {
		if lit.Value != 14 {
			t.Errorf("expected 14, got %d", lit.Value)
		}
	} else {
		t.Error("expected folded constant")
	}
}

func TestOptimizerIdentity(t *testing.T) {
	f, err := parse(`fn main() { let x = y + 0 }`)
	if err != nil {
		t.Fatal(err)
	}
	opt := NewOptimizer()
	f2 := opt.Optimize(f)
	fn := f2.Decls[0].(*FuncDecl)
	let := fn.Body[0].(*LetStmt)
	if _, ok := let.Value.(*IdentExpr); !ok {
		t.Error("expected identity to remove +0")
	}
}

func TestOptimizerMultiplyByZero(t *testing.T) {
	f, err := parse(`fn main() { let x = y * 0 }`)
	if err != nil {
		t.Fatal(err)
	}
	opt := NewOptimizer()
	f2 := opt.Optimize(f)
	fn := f2.Decls[0].(*FuncDecl)
	let := fn.Body[0].(*LetStmt)
	if lit, ok := let.Value.(*IntLit); ok {
		if lit.Value != 0 {
			t.Errorf("expected 0, got %d", lit.Value)
		}
	} else {
		t.Error("expected 0")
	}
}

func TestConstantFoldingPass(t *testing.T) {
	f, err := parse(`fn main() { let x = 10 - 3 }`)
	if err != nil {
		t.Fatal(err)
	}
	pass := &ConstantFoldingPass{}
	f2 := pass.Run(f)
	fn := f2.Decls[0].(*FuncDecl)
	let := fn.Body[0].(*LetStmt)
	if lit, ok := let.Value.(*IntLit); ok {
		if lit.Value != 7 {
			t.Errorf("expected 7, got %d", lit.Value)
		}
	} else {
		t.Error("expected folded constant")
	}
}

func TestStrengthReduction(t *testing.T) {
	f, err := parse(`fn main() { let x = y * 2 }`)
	if err != nil {
		t.Fatal(err)
	}
	pass := &StrengthReductionPass{}
	f2 := pass.Run(f)
	fn := f2.Decls[0].(*FuncDecl)
	let := fn.Body[0].(*LetStmt)
	if bin, ok := let.Value.(*BinaryExpr); ok {
		if bin.Op != "+" {
			t.Errorf("expected + (strength reduced), got %s", bin.Op)
		}
	} else {
		t.Error("expected BinaryExpr")
	}
}

func TestDeadCodeElimination(t *testing.T) {
	f, err := parse(`fn main() { return 1; let x = 2 }`)
	if err != nil {
		t.Fatal(err)
	}
	pass := &DeadCodeEliminationPass{}
	f2 := pass.Run(f)
	fn := f2.Decls[0].(*FuncDecl)
	if len(fn.Body) != 1 {
		t.Errorf("expected dead code removed, got %d stmts", len(fn.Body))
	}
}

func TestGenerateLLVM(t *testing.T) {
	f, err := parse(`fn main() -> int { return 42 }`)
	if err != nil {
		t.Fatal(err)
	}
	cg := NewCodeGenerator(TargetLLVMIR)
	ir := cg.Generate(f)
	if !strings.Contains(ir, "define i64 @main") {
		t.Errorf("expected define in LLVM IR:\n%s", ir)
	}
	if !strings.Contains(ir, "ret i64 42") {
		t.Errorf("expected ret i64 42 in IR:\n%s", ir)
	}
}

func TestGenerateC(t *testing.T) {
	f, err := parse(`fn main() -> int { return 42 }`)
	if err != nil {
		t.Fatal(err)
	}
	cg := NewCodeGenerator(TargetC)
	code := cg.Generate(f)
	if !strings.Contains(code, "long main(") {
		t.Errorf("expected C function:\n%s", code)
	}
	if !strings.Contains(code, "return 42;") {
		t.Errorf("expected return statement:\n%s", code)
	}
}

func TestGenerateWasm(t *testing.T) {
	f, err := parse(`fn main() -> int { return 42 }`)
	if err != nil {
		t.Fatal(err)
	}
	cg := NewCodeGenerator(TargetWasm)
	code := cg.Generate(f)
	if !strings.Contains(code, "(module") {
		t.Errorf("expected module:\n%s", code)
	}
}

func TestCodegenBinaryExpr(t *testing.T) {
	f, err := parse(`fn main() -> int { return 1 + 2 }`)
	if err != nil {
		t.Fatal(err)
	}
	cg := NewCodeGenerator(TargetC)
	code := cg.Generate(f)
	if !strings.Contains(code, "1 + 2") {
		t.Errorf("expected 1 + 2:\n%s", code)
	}
}

func TestCodegenIfElse(t *testing.T) {
	f, err := parse(`fn main() -> int { if x { return 1 } else { return 0 } }`)
	if err != nil {
		t.Fatal(err)
	}
	cg := NewCodeGenerator(TargetC)
	code := cg.Generate(f)
	if !strings.Contains(code, "if (") {
		t.Errorf("expected if statement:\n%s", code)
	}
}

func TestCodegenWhile(t *testing.T) {
	f, err := parse(`fn main() { while x { y = y + 1 } }`)
	if err != nil {
		t.Fatal(err)
	}
	cg := NewCodeGenerator(TargetC)
	code := cg.Generate(f)
	if !strings.Contains(code, "while (") {
		t.Errorf("expected while:\n%s", code)
	}
}

func TestTypeRefString(t *testing.T) {
	tr := &TypeRef{Name: "List", Args: []*TypeRef{{Name: "int"}}}
	if tr.String() != "List<int>" {
		t.Errorf("expected List<int>, got %s", tr.String())
	}
}

func TestBoolLiterals(t *testing.T) {
	f, err := parse(`fn main() -> bool { return true }`)
	if err != nil {
		t.Fatal(err)
	}
	fn := f.Decls[0].(*FuncDecl)
	ret := fn.Body[0].(*ReturnStmt)
	if bl, ok := ret.Value.(*BoolLit); !ok {
		t.Error("expected BoolLit")
	} else if !bl.Value {
		t.Error("expected true")
	}
}

func TestNilLiteral(t *testing.T) {
	f, err := parse(`fn main() { let x = nil }`)
	if err != nil {
		t.Fatal(err)
	}
	fn := f.Decls[0].(*FuncDecl)
	let := fn.Body[0].(*LetStmt)
	if _, ok := let.Value.(*NilLit); !ok {
		t.Error("expected NilLit")
	}
}

func TestFileGenerate(t *testing.T) {
	f, err := parse(`fn main() { return 0 }`)
	if err != nil {
		t.Fatal(err)
	}
	out := f.Generate()
	if out == "" {
		t.Error("expected non-empty output")
	}
}

func TestInliner(t *testing.T) {
	f, err := parse(`fn small() { return 1 }`)
	if err != nil {
		t.Fatal(err)
	}
	fn := f.Decls[0].(*FuncDecl)
	in := NewInliner(3)
	if !in.ShouldInline(fn) {
		t.Error("small function should be inlined")
	}
}

func TestSSAOptimizer(t *testing.T) {
	f, err := parse(`fn main() { let a = 1; let b = 2; return a }`)
	if err != nil {
		t.Fatal(err)
	}
	fn := f.Decls[0].(*FuncDecl)
	s := NewSSAOptimizer()
	stmts := s.Rename(fn.Body)
	if len(stmts) != 3 {
		t.Errorf("expected 3 stmts, got %d", len(stmts))
	}
}
