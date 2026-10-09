package lang

import (
	"fmt"
	"strings"
)

// CodeGenTarget identifies a code generation target.
type CodeGenTarget int

const (
	TargetLLVMIR CodeGenTarget = iota
	TargetC
	TargetWasm
	TargetAssembly
)

func (t CodeGenTarget) String() string {
	switch t {
	case TargetLLVMIR:
		return "llvm-ir"
	case TargetC:
		return "c"
	case TargetWasm:
		return "wasm"
	case TargetAssembly:
		return "asm"
	default:
		return "unknown"
	}
}

// CodeGenerator generates code from an AST.
type CodeGenerator struct {
	target    CodeGenTarget
	sb        strings.Builder
	indent    int
	labelNum  int
	tempNum   int
	functions map[string]*FuncDecl
	structs   map[string]*StructDecl
	enums     map[string]*EnumDecl
	scopes    []map[string]string
	currentFn *FuncDecl
}

// NewCodeGenerator creates a code generator.
func NewCodeGenerator(target CodeGenTarget) *CodeGenerator {
	return &CodeGenerator{
		target:    target,
		functions: make(map[string]*FuncDecl),
		structs:   make(map[string]*StructDecl),
		enums:     make(map[string]*EnumDecl),
		scopes:    []map[string]string{{}},
	}
}

// Generate generates code for a file.
func (cg *CodeGenerator) Generate(f *File) string {
	cg.sb.Reset()
	
	// First pass: collect declarations
	for _, d := range f.Decls {
		switch d := d.(type) {
		case *FuncDecl:
			cg.functions[d.Name] = d
		case *StructDecl:
			cg.structs[d.Name] = d
		case *EnumDecl:
			cg.enums[d.Name] = d
		}
	}
	
	switch cg.target {
	case TargetLLVMIR:
		cg.generateLLVM(f)
	case TargetC:
		cg.generateC(f)
	case TargetWasm:
		cg.generateWasm(f)
	default:
		cg.generateLLVM(f)
	}
	
	return cg.sb.String()
}

func (cg *CodeGenerator) writeIndent() {
	for i := 0; i < cg.indent; i++ {
		cg.sb.WriteString("  ")
	}
}

func (cg *CodeGenerator) writef(format string, args ...interface{}) {
	cg.writeIndent()
	cg.sb.WriteString(fmt.Sprintf(format, args...))
	cg.sb.WriteString("\n")
}

func (cg *CodeGenerator) newLabel() string {
	cg.labelNum++
	return fmt.Sprintf("L%d", cg.labelNum)
}

func (cg *CodeGenerator) newTemp() string {
	cg.tempNum++
	return fmt.Sprintf("%%t%d", cg.tempNum)
}

func (cg *CodeGenerator) pushScope() {
	cg.scopes = append(cg.scopes, make(map[string]string))
}

func (cg *CodeGenerator) popScope() {
	if len(cg.scopes) > 1 {
		cg.scopes = cg.scopes[:len(cg.scopes)-1]
	}
}

func (cg *CodeGenerator) declareVar(name, llvmType string) string {
	reg := fmt.Sprintf("%%%s", name)
	if len(cg.scopes) > 0 {
		cg.scopes[len(cg.scopes)-1][name] = reg
	}
	return reg
}

func (cg *CodeGenerator) lookupVar(name string) string {
	for i := len(cg.scopes) - 1; i >= 0; i-- {
		if r, ok := cg.scopes[i][name]; ok {
			return r
		}
	}
	return fmt.Sprintf("%%%s", name)
}

// generateLLVM generates LLVM IR.
func (cg *CodeGenerator) generateLLVM(f *File) {
	cg.sb.WriteString("; ModuleID = '" + f.Path + "'\n")
	cg.sb.WriteString("declare i32 @printf(i8*, ...)\n\n")

	for _, d := range f.Decls {
		switch d := d.(type) {
		case *FuncDecl:
			cg.generateLLVMFunc(d)
		case *StructDecl:
			cg.generateLLVMStruct(d)
		}
	}
}

func (cg *CodeGenerator) generateLLVMStruct(d *StructDecl) {
	cg.sb.WriteString(fmt.Sprintf("%%%s = type { ", d.Name))
	for i, field := range d.Fields {
		if i > 0 {
			cg.sb.WriteString(", ")
		}
		cg.sb.WriteString(llvmTypeName(field.Type))
	}
	cg.sb.WriteString(" }\n\n")
}

func llvmTypeName(t *TypeRef) string {
	if t == nil {
		return "void"
	}
	switch t.Name {
	case "i64", "int":
		return "i64"
	case "f64", "float":
		return "double"
	case "bool":
		return "i1"
	case "string":
		return "i8*"
	case "void":
		return "void"
	default:
		if len(t.Args) > 0 {
			return "%" + t.Name
		}
		return "%" + t.Name + "*"
	}
}

func (cg *CodeGenerator) generateLLVMFunc(d *FuncDecl) {
	ret := llvmTypeName(d.ReturnType)
	cg.sb.WriteString(fmt.Sprintf("define %s @%s(", ret, d.Name))
	for i, p := range d.Params {
		if i > 0 {
			cg.sb.WriteString(", ")
		}
		cg.sb.WriteString(fmt.Sprintf("%s %%%s", llvmTypeName(p.Type), p.Name))
	}
	cg.sb.WriteString(") {\n")
	cg.sb.WriteString("entry:\n")
	
	cg.pushScope()
	for _, p := range d.Params {
		cg.declareVar(p.Name, llvmTypeName(p.Type))
	}
	cg.currentFn = d
	
	cg.indent = 1
	for _, s := range d.Body {
		cg.generateLLVMStmt(s)
	}
	
	if ret == "void" {
		cg.writef("ret void")
	} else if ret == "double" {
		cg.writef("ret double 0.0")
	} else if ret == "i1" {
		cg.writef("ret i1 false")
	} else if ret == "i64" {
		cg.writef("ret i64 0")
	}
	
	cg.popScope()
	cg.indent = 0
	cg.sb.WriteString("}\n\n")
}

func (cg *CodeGenerator) generateLLVMStmt(s Stmt) {
	switch s := s.(type) {
	case *LetStmt:
		val := cg.generateLLVMExpr(s.Value)
		cg.declareVar(s.Name, llvmTypeName(s.Type))
		cg.writef("%%%s = alloca %s", s.Name, llvmTypeName(s.Type))
		cg.writef("store %s %s, %s* %%%s", llvmTypeName(s.Type), val, llvmTypeName(s.Type), s.Name)
	case *AssignStmt:
		val := cg.generateLLVMExpr(s.Value)
		cg.writef("store %s %s, %s* %%%s", llvmTypeName(nil), val, llvmTypeName(nil), s.Name)
	case *ReturnStmt:
		if s.Value == nil {
			cg.writef("ret void")
		} else {
			val := cg.generateLLVMExpr(s.Value)
			cg.writef("ret %s %s", llvmTypeName(cg.currentFn.ReturnType), val)
		}
	case *ExprStmt:
		cg.generateLLVMExpr(s.X)
	case *IfStmt:
		cond := cg.generateLLVMExpr(s.Cond)
		thenL := cg.newLabel()
		elseL := cg.newLabel()
		endL := cg.newLabel()
		cg.writef("br i1 %s, label %%%s, label %%%s", cond, thenL, elseL)
		cg.sb.WriteString("\n" + thenL + ":\n")
		cg.indent = 1
		for _, st := range s.Then {
			cg.generateLLVMStmt(st)
		}
		cg.writef("br label %%%s", endL)
		cg.sb.WriteString("\n" + elseL + ":\n")
		for _, st := range s.Else {
			cg.generateLLVMStmt(st)
		}
		cg.writef("br label %%%s", endL)
		cg.sb.WriteString("\n" + endL + ":\n")
	case *WhileStmt:
		condL := cg.newLabel()
		bodyL := cg.newLabel()
		endL := cg.newLabel()
		cg.writef("br label %%%s", condL)
		cg.sb.WriteString("\n" + condL + ":\n")
		c := cg.generateLLVMExpr(s.Cond)
		cg.writef("br i1 %s, label %%%s, label %%%s", c, bodyL, endL)
		cg.sb.WriteString("\n" + bodyL + ":\n")
		for _, st := range s.Body {
			cg.generateLLVMStmt(st)
		}
		cg.writef("br label %%%s", condL)
		cg.sb.WriteString("\n" + endL + ":\n")
	case *ForStmt:
		// Simplified: treat as while
		condL := cg.newLabel()
		bodyL := cg.newLabel()
		endL := cg.newLabel()
		cg.writef("br label %%%s", condL)
		cg.sb.WriteString("\n" + condL + ":\n")
		cg.writef("br label %%%s", bodyL)
		cg.sb.WriteString("\n" + bodyL + ":\n")
		for _, st := range s.Body {
			cg.generateLLVMStmt(st)
		}
		cg.writef("br label %%%s", endL)
		cg.sb.WriteString("\n" + endL + ":\n")
	}
}

func (cg *CodeGenerator) generateLLVMExpr(e Expr) string {
	switch e := e.(type) {
	case *IntLit:
		return fmt.Sprintf("%d", e.Value)
	case *FloatLit:
		return fmt.Sprintf("%f", e.Value)
	case *StringLit:
		tmp := cg.newTemp()
		cg.tempNum++
		cg.writef("%s = getelementptr [%d x i8], [%d x i8]* @.str, i64 0, i64 0", tmp, len(e.Value)+1, len(e.Value)+1)
		return tmp
	case *BoolLit:
		if e.Value {
			return "true"
		}
		return "false"
	case *NilLit:
		return "null"
	case *IdentExpr:
		tmp := cg.newTemp()
		cg.writef("%s = load %s, %s* %%%s", tmp, llvmTypeName(nil), llvmTypeName(nil), e.Name)
		return tmp
	case *BinaryExpr:
		l := cg.generateLLVMExpr(e.Left)
		r := cg.generateLLVMExpr(e.Right)
		tmp := cg.newTemp()
		switch e.Op {
		case "+", "-", "*", "/", "%":
			cg.writef("%s = %s i64 %s, %s", tmp, llvmBinOp(e.Op), l, r)
		case "==", "!=", "<", ">", "<=", ">=":
			cg.writef("%s = icmp %s i64 %s, %s", tmp, llvmICmpOp(e.Op), l, r)
		default:
			cg.writef("%s = %s i64 %s, %s", tmp, llvmBinOp(e.Op), l, r)
		}
		return tmp
	case *UnaryExpr:
		v := cg.generateLLVMExpr(e.Expr)
		tmp := cg.newTemp()
		if e.Op == "-" {
			cg.writef("%s = sub i64 0, %s", tmp, v)
		}
		return tmp
	case *CallExpr:
		tmp := cg.newTemp()
		cg.writef("%s = call i64 @%s(...)", tmp, exprName(e.Callee))
		return tmp
	case *IfExpr:
		cond := cg.generateLLVMExpr(e.Cond)
		tmp := cg.newTemp()
		cg.writef("%s = select i1 %s, i64 1, i64 0", tmp, cond)
		return tmp
	}
	return "0"
}

func exprName(e Expr) string {
	switch e := e.(type) {
	case *IdentExpr:
		return e.Name
	case *FieldExpr:
		return exprName(e.Object) + "." + e.Field
	case *MethodExpr:
		return exprName(e.Object) + "." + e.Method
	}
	return "?"
}

func llvmBinOp(op string) string {
	switch op {
	case "+":
		return "add"
	case "-":
		return "sub"
	case "*":
		return "mul"
	case "/":
		return "sdiv"
	case "%":
		return "srem"
	case "&":
		return "and"
	case "|":
		return "or"
	case "^":
		return "xor"
	}
	return "add"
}

func llvmICmpOp(op string) string {
	switch op {
	case "==":
		return "eq"
	case "!=":
		return "ne"
	case "<":
		return "slt"
	case ">":
		return "sgt"
	case "<=":
		return "sle"
	case ">=":
		return "sge"
	}
	return "eq"
}

// generateC generates C code.
func (cg *CodeGenerator) generateC(f *File) {
	cg.sb.WriteString("#include <stdio.h>\n")
	cg.sb.WriteString("#include <stdlib.h>\n")
	cg.sb.WriteString("#include <string.h>\n\n")

	for _, d := range f.Decls {
		switch d := d.(type) {
		case *FuncDecl:
			cg.generateCFunc(d)
		case *StructDecl:
			cg.generateCStruct(d)
		}
	}
}

func cTypeName(t *TypeRef) string {
	if t == nil {
		return "void"
	}
	switch t.Name {
	case "i64", "int":
		return "long"
	case "f64", "float":
		return "double"
	case "bool":
		return "int"
	case "string":
		return "char*"
	case "void":
		return "void"
	default:
		return "void*"
	}
}

func (cg *CodeGenerator) generateCStruct(d *StructDecl) {
	cg.sb.WriteString("typedef struct {\n")
	for _, field := range d.Fields {
		cg.sb.WriteString(fmt.Sprintf("    %s %s;\n", cTypeName(field.Type), field.Name))
	}
	cg.sb.WriteString(fmt.Sprintf("} %s;\n\n", d.Name))
}

func (cg *CodeGenerator) generateCFunc(d *FuncDecl) {
	cg.sb.WriteString(fmt.Sprintf("%s %s(", cTypeName(d.ReturnType), d.Name))
	for i, p := range d.Params {
		if i > 0 {
			cg.sb.WriteString(", ")
		}
		cg.sb.WriteString(fmt.Sprintf("%s %s", cTypeName(p.Type), p.Name))
	}
	cg.sb.WriteString(") {\n")
	
	cg.pushScope()
	for _, p := range d.Params {
		cg.declareVar(p.Name, cTypeName(p.Type))
	}
	cg.currentFn = d
	
	cg.indent = 1
	for _, s := range d.Body {
		cg.generateCStmt(s)
	}
	
	cg.popScope()
	cg.indent = 0
	cg.sb.WriteString("}\n\n")
}

func (cg *CodeGenerator) generateCStmt(s Stmt) {
	switch s := s.(type) {
	case *LetStmt:
		cg.writef("%s %s = %s;", cTypeName(s.Type), s.Name, cg.generateCExpr(s.Value))
	case *AssignStmt:
		cg.writef("%s = %s;", s.Name, cg.generateCExpr(s.Value))
	case *ReturnStmt:
		if s.Value == nil {
			cg.writef("return;")
		} else {
			cg.writef("return %s;", cg.generateCExpr(s.Value))
		}
	case *ExprStmt:
		cg.writef("%s;", cg.generateCExpr(s.X))
	case *IfStmt:
		cg.writef("if (%s) {", cg.generateCExpr(s.Cond))
		cg.indent++
		for _, st := range s.Then {
			cg.generateCStmt(st)
		}
		cg.indent--
		if len(s.Else) > 0 {
			cg.writef("} else {")
			cg.indent++
			for _, st := range s.Else {
				cg.generateCStmt(st)
			}
			cg.indent--
		}
		cg.writef("}")
	case *WhileStmt:
		cg.writef("while (%s) {", cg.generateCExpr(s.Cond))
		cg.indent++
		for _, st := range s.Body {
			cg.generateCStmt(st)
		}
		cg.indent--
		cg.writef("}")
	case *ForStmt:
		cg.writef("for (int %s : %s) {", s.Var, cg.generateCExpr(s.Iter))
		cg.indent++
		for _, st := range s.Body {
			cg.generateCStmt(st)
		}
		cg.indent--
		cg.writef("}")
	case *BlockStmt:
		cg.writef("{")
		cg.indent++
		for _, st := range s.Stmts {
			cg.generateCStmt(st)
		}
		cg.indent--
		cg.writef("}")
	}
}

func (cg *CodeGenerator) generateCExpr(e Expr) string {
	switch e := e.(type) {
	case *IntLit:
		return fmt.Sprintf("%d", e.Value)
	case *FloatLit:
		return fmt.Sprintf("%f", e.Value)
	case *StringLit:
		return fmt.Sprintf("%q", e.Value)
	case *BoolLit:
		if e.Value {
			return "1"
		}
		return "0"
	case *NilLit:
		return "NULL"
	case *IdentExpr:
		return e.Name
	case *BinaryExpr:
		return fmt.Sprintf("(%s %s %s)", cg.generateCExpr(e.Left), e.Op, cg.generateCExpr(e.Right))
	case *UnaryExpr:
		return fmt.Sprintf("(%s%s)", e.Op, cg.generateCExpr(e.Expr))
	case *CallExpr:
		args := make([]string, len(e.Args))
		for i, a := range e.Args {
			args[i] = cg.generateCExpr(a)
		}
		return fmt.Sprintf("%s(%s)", exprName(e.Callee), strings.Join(args, ", "))
	}
	return "0"
}

// generateWasm generates WebAssembly text format.
func (cg *CodeGenerator) generateWasm(f *File) {
	cg.sb.WriteString("(module\n")
	for _, d := range f.Decls {
		fn, ok := d.(*FuncDecl)
		if !ok || fn.Name != "main" {
			continue
		}
		cg.sb.WriteString("  (func $main (result i32)\n")
		cg.indent = 4
		for _, s := range fn.Body {
			cg.generateWasmStmt(s)
		}
		cg.writef("i32.const 0")
		cg.indent = 2
		cg.sb.WriteString("  )\n")
	}
	cg.sb.WriteString("  (export \"main\" (func $main))\n")
	cg.sb.WriteString(")\n")
}

func (cg *CodeGenerator) generateWasmStmt(s Stmt) {
	switch s := s.(type) {
	case *ReturnStmt:
		if s.Value != nil {
			cg.writef("i32.const %s", cg.generateWasmExpr(s.Value))
		} else {
			cg.writef("i32.const 0")
		}
	case *ExprStmt:
		cg.generateWasmExpr(s.X)
	case *IfStmt:
		cg.writef("if")
		cg.generateWasmExpr(s.Cond)
		cg.indent++
		for _, st := range s.Then {
			cg.generateWasmStmt(st)
		}
		cg.indent--
		cg.writef("end")
	}
}

func (cg *CodeGenerator) generateWasmExpr(e Expr) string {
	switch e := e.(type) {
	case *IntLit:
		cg.writef("i32.const %d", e.Value)
		return fmt.Sprintf("%d", e.Value)
	case *IdentExpr:
		return fmt.Sprintf("$%s", e.Name)
	case *BinaryExpr:
		cg.generateWasmExpr(e.Left)
		cg.generateWasmExpr(e.Right)
		switch e.Op {
		case "+":
			cg.writef("i32.add")
		case "-":
			cg.writef("i32.sub")
		case "*":
			cg.writef("i32.mul")
		case "/":
			cg.writef("i32.div_s")
		}
		return ""
	}
	return "0"
}