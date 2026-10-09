package lang

import (
	"fmt"
	"strconv"
)

// Node is the interface for all AST nodes.
type Node interface {
	String() string
	Pos() (line, col int)
}

// Expr is the interface for expression nodes.
type Expr interface {
	Node
	exprNode()
}

// Stmt is the interface for statement nodes.
type Stmt interface {
	Node
	stmtNode()
}

// Decl is the interface for declaration nodes.
type Decl interface {
	Node
	declNode()
}

// Literal kinds.
type (
	// IntLit is an integer literal.
	IntLit struct {
		Value int64
		Line  int
		Col   int
	}
	// FloatLit is a float literal.
	FloatLit struct {
		Value float64
		Line  int
		Col   int
	}
	// StringLit is a string literal.
	StringLit struct {
		Value string
		Line  int
		Col   int
	}
	// BoolLit is a boolean literal.
	BoolLit struct {
		Value bool
		Line  int
		Col   int
	}
	// NilLit is a nil literal.
	NilLit struct {
		Line int
		Col  int
	}
)

func (e *IntLit) exprNode()    {}
func (e *FloatLit) exprNode()  {}
func (e *StringLit) exprNode() {}
func (e *BoolLit) exprNode()   {}
func (e *NilLit) exprNode()    {}

func (e *IntLit) String() string   { return strconv.FormatInt(e.Value, 10) }
func (e *FloatLit) String() string { return strconv.FormatFloat(e.Value, 'g', -1, 64) }
func (e *StringLit) String() string { return fmt.Sprintf("%q", e.Value) }
func (e *BoolLit) String() string   { return strconv.FormatBool(e.Value) }
func (e *NilLit) String() string    { return "nil" }

func (e *IntLit) Pos() (int, int)   { return e.Line, e.Col }
func (e *FloatLit) Pos() (int, int) { return e.Line, e.Col }
func (e *StringLit) Pos() (int, int) { return e.Line, e.Col }
func (e *BoolLit) Pos() (int, int)  { return e.Line, e.Col }
func (e *NilLit) Pos() (int, int)   { return e.Line, e.Col }

// IdentExpr is an identifier reference.
type IdentExpr struct {
	Name string
	Line int
	Col  int
}

func (e *IdentExpr) exprNode()          {}
func (e *IdentExpr) String() string     { return e.Name }
func (e *IdentExpr) Pos() (int, int)    { return e.Line, e.Col }

// BinaryExpr is a binary operation.
type BinaryExpr struct {
	Op    string
	Left  Expr
	Right Expr
	Line  int
	Col   int
}

func (e *BinaryExpr) exprNode()       {}
func (e *BinaryExpr) String() string  { return fmt.Sprintf("(%s %s %s)", e.Op, e.Left, e.Right) }
func (e *BinaryExpr) Pos() (int, int) { return e.Line, e.Col }

// UnaryExpr is a unary operation.
type UnaryExpr struct {
	Op   string
	Expr Expr
	Line int
	Col  int
}

func (e *UnaryExpr) exprNode()      {}
func (e *UnaryExpr) String() string { return fmt.Sprintf("(%s%s)", e.Op, e.Expr) }
func (e *UnaryExpr) Pos() (int, int) { return e.Line, e.Col }

// CallExpr is a function call.
type CallExpr struct {
	Callee Expr
	Args   []Expr
	Line   int
	Col    int
}

func (e *CallExpr) exprNode()      {}
func (e *CallExpr) String() string { return fmt.Sprintf("%s(...)", e.Callee) }
func (e *CallExpr) Pos() (int, int) { return e.Line, e.Col }

// IndexExpr is an index expression.
type IndexExpr struct {
	Object Expr
	Index  Expr
	Line   int
	Col    int
}

func (e *IndexExpr) exprNode()      {}
func (e *IndexExpr) String() string { return fmt.Sprintf("%s[%s]", e.Object, e.Index) }
func (e *IndexExpr) Pos() (int, int) { return e.Line, e.Col }

// FieldExpr is a struct field access.
type FieldExpr struct {
	Object Expr
	Field  string
	Line   int
	Col    int
}

func (e *FieldExpr) exprNode()      {}
func (e *FieldExpr) String() string { return fmt.Sprintf("%s.%s", e.Object, e.Field) }
func (e *FieldExpr) Pos() (int, int) { return e.Line, e.Col }

// IfExpr is a conditional expression.
type IfExpr struct {
	Cond Expr
	Then Expr
	Else Expr
	Line int
	Col  int
}

func (e *IfExpr) exprNode()      {}
func (e *IfExpr) String() string { return fmt.Sprintf("if %s { %s } else { %s }", e.Cond, e.Then, e.Else) }
func (e *IfExpr) Pos() (int, int) { return e.Line, e.Col }

// StructLitExpr is a struct literal.
type StructLitExpr struct {
	Name   string
	Fields []FieldAssign
	Line   int
	Col    int
}

// FieldAssign is a field assignment in a struct literal.
type FieldAssign struct {
	Name  string
	Value Expr
}

func (e *StructLitExpr) exprNode()      {}
func (e *StructLitExpr) String() string { return fmt.Sprintf("%s{...}", e.Name) }
func (e *StructLitExpr) Pos() (int, int) { return e.Line, e.Col }

// MethodExpr represents a method call.
type MethodExpr struct {
	Object Expr
	Method string
	Args   []Expr
	Line   int
	Col    int
}

func (e *MethodExpr) exprNode()      {}
func (e *MethodExpr) String() string { return fmt.Sprintf("%s.%s(...)", e.Object, e.Method) }
func (e *MethodExpr) Pos() (int, int) { return e.Line, e.Col }

// Statements.

// ExprStmt is an expression statement.
type ExprStmt struct {
	X Expr
}

func (s *ExprStmt) stmtNode()       {}
func (s *ExprStmt) String() string  { return s.X.String() }
func (s *ExprStmt) Pos() (int, int) { return s.X.Pos() }

// LetStmt is a let binding.
type LetStmt struct {
	Name  string
	Value Expr
	Mut   bool
	Type  *TypeRef
	Line  int
	Col   int
}

func (s *LetStmt) stmtNode()      {}
func (s *LetStmt) String() string { return fmt.Sprintf("let %s = %s", s.Name, s.Value) }
func (s *LetStmt) Pos() (int, int) { return s.Line, s.Col }

// AssignStmt is an assignment.
type AssignStmt struct {
	Name  string
	Value Expr
	Line  int
	Col   int
}

func (s *AssignStmt) stmtNode()      {}
func (s *AssignStmt) String() string { return fmt.Sprintf("%s = %s", s.Name, s.Value) }
func (s *AssignStmt) Pos() (int, int) { return s.Line, s.Col }

// ReturnStmt is a return statement.
type ReturnStmt struct {
	Value Expr
	Line  int
	Col   int
}

func (s *ReturnStmt) stmtNode()      {}
func (s *ReturnStmt) String() string { return fmt.Sprintf("return %s", s.Value) }
func (s *ReturnStmt) Pos() (int, int) { return s.Line, s.Col }

// IfStmt is an if statement.
type IfStmt struct {
	Cond Expr
	Then []Stmt
	Else []Stmt
	Line int
	Col  int
}

func (s *IfStmt) stmtNode()      {}
func (s *IfStmt) String() string { return "if ... else ..." }
func (s *IfStmt) Pos() (int, int) { return s.Line, s.Col }

// WhileStmt is a while loop.
type WhileStmt struct {
	Cond Expr
	Body []Stmt
	Line int
	Col  int
}

func (s *WhileStmt) stmtNode()      {}
func (s *WhileStmt) String() string { return "while ..." }
func (s *WhileStmt) Pos() (int, int) { return s.Line, s.Col }

// ForStmt is a for-in loop.
type ForStmt struct {
	Var   string
	Iter  Expr
	Body  []Stmt
	Line  int
	Col   int
}

func (s *ForStmt) stmtNode()      {}
func (s *ForStmt) String() string { return fmt.Sprintf("for %s in ...", s.Var) }
func (s *ForStmt) Pos() (int, int) { return s.Line, s.Col }

// BreakStmt breaks a loop.
type BreakStmt struct{ Line, Col int }

func (s *BreakStmt) stmtNode()       {}
func (s *BreakStmt) String() string  { return "break" }
func (s *BreakStmt) Pos() (int, int) { return s.Line, s.Col }

// ContinueStmt continues a loop.
type ContinueStmt struct{ Line, Col int }

func (s *ContinueStmt) stmtNode()       {}
func (s *ContinueStmt) String() string  { return "continue" }
func (s *ContinueStmt) Pos() (int, int) { return s.Line, s.Col }

// BlockStmt is a block of statements.
type BlockStmt struct {
	Stmts []Stmt
	Line  int
	Col   int
}

func (s *BlockStmt) stmtNode()      {}
func (s *BlockStmt) String() string { return "{ ... }" }
func (s *BlockStmt) Pos() (int, int) { return s.Line, s.Col }

// TypeRef is a type reference.
type TypeRef struct {
	Name string
	Args []*TypeRef
	Line int
	Col  int
}

func (t *TypeRef) String() string {
	if len(t.Args) == 0 {
		return t.Name
	}
	s := t.Name + "<"
	for i, a := range t.Args {
		if i > 0 {
			s += ", "
		}
		s += a.String()
	}
	return s + ">"
}

// Declarations.

// FuncDecl is a function declaration.
type FuncDecl struct {
	Name       string
	Params     []Param
	ReturnType *TypeRef
	Body       []Stmt
	Generics   []string
	Line       int
	Col        int
}

// Param is a function parameter.
type Param struct {
	Name string
	Type *TypeRef
}

func (d *FuncDecl) declNode()      {}
func (d *FuncDecl) String() string { return fmt.Sprintf("fn %s(...)", d.Name) }
func (d *FuncDecl) Pos() (int, int) { return d.Line, d.Col }

// StructDecl is a struct declaration.
type StructDecl struct {
	Name     string
	Fields   []Field
	Generics []string
	Methods  []*FuncDecl
	Line     int
	Col      int
}

// Field is a struct field.
type Field struct {
	Name string
	Type *TypeRef
}

func (d *StructDecl) declNode()      {}
func (d *StructDecl) String() string { return fmt.Sprintf("struct %s", d.Name) }
func (d *StructDecl) Pos() (int, int) { return d.Line, d.Col }

// EnumDecl is an enum declaration.
type EnumDecl struct {
	Name     string
	Variants []string
	Line     int
	Col      int
}

func (d *EnumDecl) declNode()      {}
func (d *EnumDecl) String() string { return fmt.Sprintf("enum %s", d.Name) }
func (d *EnumDecl) Pos() (int, int) { return d.Line, d.Col }

// ImportDecl is an import declaration.
type ImportDecl struct {
	Path string
	As   string
	Line int
	Col  int
}

func (d *ImportDecl) declNode()      {}
func (d *ImportDecl) String() string { return fmt.Sprintf("import %q", d.Path) }
func (d *ImportDecl) Pos() (int, int) { return d.Line, d.Col }

// File is a parsed source file.
type File struct {
	Decls []Decl
	Path  string
}

// Parser parses tokens into an AST.
type Parser struct {
	tokens []Token
	pos    int
	errors []string
}

// NewParser creates a new parser.
func NewParser(tokens []Token) *Parser {
	return &Parser{tokens: tokens}
}

func (p *Parser) current() Token {
	if p.pos < len(p.tokens) {
		return p.tokens[p.pos]
	}
	return Token{Type: TokenEOF}
}

func (p *Parser) peek(n int) Token {
	if p.pos+n < len(p.tokens) {
		return p.tokens[p.pos+n]
	}
	return Token{Type: TokenEOF}
}

func (p *Parser) advance() Token {
	t := p.current()
	if p.pos < len(p.tokens) {
		p.pos++
	}
	return t
}

// skipSeparators skips newlines, comments and statement separators.
func (p *Parser) skipSeparators() {
	for p.current().Type == TokenNewline || p.current().Type == TokenComment ||
		(p.current().Type == TokenDelimiter && p.current().Value == ";") {
		p.pos++
	}
}

func (p *Parser) skipNewlines() {
	for p.current().Type == TokenNewline || p.current().Type == TokenComment {
		p.pos++
	}
}

func (p *Parser) expect(tt TokenType, val string) (Token, error) {
	t := p.current()
	if t.Type != tt || (val != "" && t.Value != val) {
		return t, fmt.Errorf("expected %s %q, got %s %q at L%d:C%d", tt, val, t.Type, t.Value, t.Line, t.Col)
	}
	p.advance()
	return t, nil
}

// Parse parses the token stream into a File.
func (p *Parser) Parse() (*File, error) {
	file := &File{}
	p.skipNewlines()
	for p.current().Type != TokenEOF {
		decl, err := p.parseDecl()
		if err != nil {
			p.errors = append(p.errors, err.Error())
			p.recover()
			continue
		}
		if decl != nil {
			file.Decls = append(file.Decls, decl)
		}
		p.skipNewlines()
	}
	if len(p.errors) > 0 {
		return nil, fmt.Errorf("parser errors: %v", p.errors)
	}
	return file, nil
}

func (p *Parser) recover() {
	for p.current().Type != TokenEOF && p.current().Type != TokenNewline {
		p.advance()
	}
	p.skipNewlines()
}

func (p *Parser) parseDecl() (Decl, error) {
	t := p.current()
	if t.Type == TokenKeyword {
		switch t.Value {
		case "fn":
			return p.parseFuncDecl()
		case "struct":
			return p.parseStructDecl()
		case "enum":
			return p.parseEnumDecl()
		case "import":
			return p.parseImportDecl()
		case "export":
			p.advance()
			return p.parseDecl()
		}
	}
	return nil, fmt.Errorf("unexpected token %s %q at L%d:C%d", t.Type, t.Value, t.Line, t.Col)
}

func (p *Parser) parseFuncDecl() (Decl, error) {
	kw := p.expectKeyword("fn")
	name := p.advance()
	if name.Type != TokenIdent {
		return nil, fmt.Errorf("expected function name at L%d:C%d", kw.Line, kw.Col)
	}

	generic := []string{}
	if p.current().Value == "<" && p.current().Type == TokenOperator {
		p.advance()
		for p.current().Value != ">" {
			id := p.advance()
			if id.Type == TokenIdent {
				generic = append(generic, id.Value)
			}
			if p.current().Value == "," {
				p.advance()
			}
		}
		p.advance() // >
	}

	if _, err := p.expect(TokenDelimiter, "("); err != nil {
		return nil, err
	}
	params := []Param{}
	for p.current().Value != ")" {
		pn := p.advance()
		if p.current().Value == ":" {
			p.advance()
		}
		pt := p.parseTypeRef()
		params = append(params, Param{Name: pn.Value, Type: pt})
		if p.current().Value == "," {
			p.advance()
		} else {
			break
		}
	}
	p.expect(TokenDelimiter, ")")

	var retType *TypeRef
	if p.current().Value == "->" {
		p.advance()
		retType = p.parseTypeRef()
	}

	body, err := p.parseBlock()
	if err != nil {
		return nil, err
	}

	return &FuncDecl{
		Name: name.Value, Params: params, ReturnType: retType,
		Body: body, Generics: generic, Line: kw.Line, Col: kw.Col,
	}, nil
}

func (p *Parser) expectKeyword(kw string) Token {
	t := p.current()
	if t.Type == TokenKeyword && t.Value == kw {
		p.advance()
		return t
	}
	p.errors = append(p.errors, fmt.Sprintf("expected keyword %q at L%d:C%d", kw, t.Line, t.Col))
	return t
}

func (p *Parser) parseStructDecl() (Decl, error) {
	kw := p.expectKeyword("struct")
	name := p.advance()
	generic := []string{}
	if p.current().Value == "<" && p.current().Type == TokenOperator {
		p.advance()
		for p.current().Value != ">" {
			id := p.advance()
			if id.Type == TokenIdent {
				generic = append(generic, id.Value)
			}
			if p.current().Value == "," {
				p.advance()
			}
		}
		p.advance()
	}
	p.expect(TokenDelimiter, "{")
	fields := []Field{}
	methods := []*FuncDecl{}
	p.skipNewlines()
	for p.current().Value != "}" && p.current().Type != TokenEOF {
		if p.current().Type == TokenKeyword && p.current().Value == "fn" {
			m, err := p.parseFuncDecl()
			if err == nil {
				if fd, ok := m.(*FuncDecl); ok {
					methods = append(methods, fd)
				}
			}
		} else {
			fn := p.advance()
			if p.current().Value == ":" {
				p.advance()
			}
			ft := p.parseTypeRef()
			fields = append(fields, Field{Name: fn.Value, Type: ft})
			if p.current().Value == "," {
				p.advance()
			}
			p.skipSeparators()
		}
		p.skipNewlines()
	}
	p.expect(TokenDelimiter, "}")
	return &StructDecl{Name: name.Value, Fields: fields, Generics: generic, Methods: methods, Line: kw.Line, Col: kw.Col}, nil
}

func (p *Parser) parseEnumDecl() (Decl, error) {
	kw := p.expectKeyword("enum")
	name := p.advance()
	p.expect(TokenDelimiter, "{")
	variants := []string{}
	p.skipNewlines()
	for p.current().Value != "}" && p.current().Type != TokenEOF {
		v := p.advance()
		variants = append(variants, v.Value)
		if p.current().Value == "," {
			p.advance()
		}
		p.skipNewlines()
	}
	p.expect(TokenDelimiter, "}")
	return &EnumDecl{Name: name.Value, Variants: variants, Line: kw.Line, Col: kw.Col}, nil
}

func (p *Parser) parseImportDecl() (Decl, error) {
	kw := p.expectKeyword("import")
	str := p.advance()
	as := ""
	if p.current().Type == TokenKeyword && p.current().Value == "as" {
		p.advance()
		as = p.advance().Value
	}
	return &ImportDecl{Path: str.Value, As: as, Line: kw.Line, Col: kw.Col}, nil
}

func (p *Parser) parseTypeRef() *TypeRef {
	t := p.current()
	if t.Type != TokenIdent {
		return &TypeRef{Name: "unknown", Line: t.Line, Col: t.Col}
	}
	p.advance()
	ref := &TypeRef{Name: t.Value, Line: t.Line, Col: t.Col}
	if p.current().Value == "<" && p.current().Type == TokenOperator {
		p.advance()
		for p.current().Value != ">" {
			ref.Args = append(ref.Args, p.parseTypeRef())
			if p.current().Value == "," {
				p.advance()
			}
		}
		p.advance()
	}
	return ref
}

func (p *Parser) parseBlock() ([]Stmt, error) {
	tok, err := p.expect(TokenDelimiter, "{")
	if err != nil {
		return nil, err
	}
	stmts := []Stmt{}
	p.skipSeparators()
	for p.current().Value != "}" && p.current().Type != TokenEOF {
		s, err := p.parseStmt()
		if err != nil {
			return nil, err
		}
		if s != nil {
			stmts = append(stmts, s)
		}
		p.skipSeparators()
	}
	if _, err := p.expect(TokenDelimiter, "}"); err != nil {
		return nil, err
	}
	_ = tok
	return stmts, nil
}

func (p *Parser) parseStmt() (Stmt, error) {
	t := p.current()
	if t.Type == TokenKeyword {
		switch t.Value {
		case "let":
			return p.parseLet()
		case "return":
			return p.parseReturn()
		case "if":
			return p.parseIf()
		case "while":
			return p.parseWhile()
		case "for":
			return p.parseFor()
		case "break":
			p.advance()
			return &BreakStmt{Line: t.Line, Col: t.Col}, nil
		case "continue":
			p.advance()
			return &ContinueStmt{Line: t.Line, Col: t.Col}, nil
		}
	}
	return p.parseSimpleStmt()
}

func (p *Parser) parseLet() (Stmt, error) {
	kw := p.advance() // let
	mut := false
	if p.current().Type == TokenKeyword && p.current().Value == "mut" {
		mut = true
		p.advance()
	}
	name := p.advance()
	var typeRef *TypeRef
	if p.current().Value == ":" {
		p.advance()
		typeRef = p.parseTypeRef()
	}
	p.expect(TokenOperator, "=")
	val, err := p.parseExpr()
	if err != nil {
		return nil, err
	}
	return &LetStmt{Name: name.Value, Value: val, Mut: mut, Type: typeRef, Line: kw.Line, Col: kw.Col}, nil
}

func (p *Parser) parseReturn() (Stmt, error) {
	kw := p.advance()
	if p.current().Type == TokenNewline || p.current().Value == "}" {
		return &ReturnStmt{Value: nil, Line: kw.Line, Col: kw.Col}, nil
	}
	val, err := p.parseExpr()
	if err != nil {
		return nil, err
	}
	return &ReturnStmt{Value: val, Line: kw.Line, Col: kw.Col}, nil
}

func (p *Parser) parseIf() (Stmt, error) {
	kw := p.advance()
	cond, err := p.parseExpr()
	if err != nil {
		return nil, err
	}
	then, err := p.parseBlock()
	if err != nil {
		return nil, err
	}
	var elseBlock []Stmt
	p.skipNewlines()
	if p.current().Type == TokenKeyword && p.current().Value == "else" {
		p.advance()
		if p.current().Type == TokenKeyword && p.current().Value == "if" {
			es, err := p.parseIf()
			if err != nil {
				return nil, err
			}
			elseBlock = []Stmt{es}
		} else {
			eb, err := p.parseBlock()
			if err != nil {
				return nil, err
			}
			elseBlock = eb
		}
	}
	return &IfStmt{Cond: cond, Then: then, Else: elseBlock, Line: kw.Line, Col: kw.Col}, nil
}

func (p *Parser) parseWhile() (Stmt, error) {
	kw := p.advance()
	cond, err := p.parseExpr()
	if err != nil {
		return nil, err
	}
	body, err := p.parseBlock()
	if err != nil {
		return nil, err
	}
	return &WhileStmt{Cond: cond, Body: body, Line: kw.Line, Col: kw.Col}, nil
}

func (p *Parser) parseFor() (Stmt, error) {
	kw := p.advance()
	varName := p.advance()
	if !(p.current().Type == TokenKeyword && p.current().Value == "in") {
		return nil, fmt.Errorf("expected 'in' in for loop at L%d:C%d", kw.Line, kw.Col)
	}
	p.advance()
	iter, err := p.parseExpr()
	if err != nil {
		return nil, err
	}
	body, err := p.parseBlock()
	if err != nil {
		return nil, err
	}
	return &ForStmt{Var: varName.Value, Iter: iter, Body: body, Line: kw.Line, Col: kw.Col}, nil
}

func (p *Parser) parseSimpleStmt() (Stmt, error) {
	t := p.current()
	// Assignment detection: ident = expr
	if t.Type == TokenIdent && p.peek(1).Type == TokenOperator && p.peek(1).Value == "=" {
		p.advance()
		p.advance()
		val, err := p.parseExpr()
		if err != nil {
			return nil, err
		}
		return &AssignStmt{Name: t.Value, Value: val, Line: t.Line, Col: t.Col}, nil
	}
	x, err := p.parseExpr()
	if err != nil {
		return nil, err
	}
	return &ExprStmt{X: x}, nil
}

// Expression parsing with precedence climbing.
func (p *Parser) parseExpr() (Expr, error) {
	return p.parseBinary(0)
}

var precedence = map[string]int{
	"=": 1, "+=": 1, "-=": 1, "*=": 1, "/=": 1,
	"||": 2,
	"&&": 3,
	"==": 4, "!=": 4,
	"<": 5, ">": 5, "<=": 5, ">=": 5,
	"+": 6, "-": 6,
	"*": 7, "/": 7, "%": 7,
	"..": 8,
}

func (p *Parser) parseBinary(minPrec int) (Expr, error) {
	left, err := p.parseUnary()
	if err != nil {
		return nil, err
	}
	for {
		t := p.current()
		if t.Type != TokenOperator {
			break
		}
		prec := precedence[t.Value]
		if prec < minPrec || prec == 0 {
			break
		}
		op := t.Value
		line, col := t.Line, t.Col
		p.advance()
		right, err := p.parseBinary(prec + 1)
		if err != nil {
			return nil, err
		}
		left = &BinaryExpr{Op: op, Left: left, Right: right, Line: line, Col: col}
	}
	return left, nil
}

func (p *Parser) parseUnary() (Expr, error) {
	t := p.current()
	if t.Type == TokenOperator && (t.Value == "-" || t.Value == "!" || t.Value == "~") {
		p.advance()
		x, err := p.parseUnary()
		if err != nil {
			return nil, err
		}
		return &UnaryExpr{Op: t.Value, Expr: x, Line: t.Line, Col: t.Col}, nil
	}
	return p.parsePostfix()
}

func (p *Parser) parsePostfix() (Expr, error) {
	x, err := p.parsePrimary()
	if err != nil {
		return nil, err
	}
	for {
		t := p.current()
		if t.Type == TokenDelimiter && t.Value == "(" {
			p.advance()
			args := []Expr{}
			for p.current().Value != ")" {
				a, err := p.parseExpr()
				if err != nil {
					return nil, err
				}
				args = append(args, a)
				if p.current().Value == "," {
					p.advance()
				} else {
					break
				}
			}
			p.expect(TokenDelimiter, ")")
			x = &CallExpr{Callee: x, Args: args, Line: t.Line, Col: t.Col}
		} else if t.Type == TokenDelimiter && t.Value == "[" {
			p.advance()
			idx, err := p.parseExpr()
			if err != nil {
				return nil, err
			}
			p.expect(TokenDelimiter, "]")
			x = &IndexExpr{Object: x, Index: idx, Line: t.Line, Col: t.Col}
		} else if t.Type == TokenOperator && t.Value == "." {
			p.advance()
			field := p.advance()
			x = &FieldExpr{Object: x, Field: field.Value, Line: t.Line, Col: t.Col}
		} else {
			break
		}
	}
	return x, nil
}

func (p *Parser) parsePrimary() (Expr, error) {
	t := p.current()
	switch t.Type {
	case TokenInt:
		p.advance()
		v, err := strconv.ParseInt(t.Value, 0, 64)
		if err != nil {
			return nil, fmt.Errorf("invalid int literal %q: %v", t.Value, err)
		}
		return &IntLit{Value: v, Line: t.Line, Col: t.Col}, nil
	case TokenFloat:
		p.advance()
		v, err := strconv.ParseFloat(t.Value, 64)
		if err != nil {
			return nil, fmt.Errorf("invalid float literal %q: %v", t.Value, err)
		}
		return &FloatLit{Value: v, Line: t.Line, Col: t.Col}, nil
	case TokenString:
		p.advance()
		return &StringLit{Value: t.Value, Line: t.Line, Col: t.Col}, nil
	case TokenIdent:
		// Struct literal: Name{...} — only when name is a type-like
		// (uppercase first letter) and followed by a brace.
		if isTypeName(t.Value) && p.peek(1).Type == TokenDelimiter && p.peek(1).Value == "{" {
			p.advance()
			p.advance()
			fields := []FieldAssign{}
			for p.current().Value != "}" {
				fname := p.advance()
				p.expect(TokenOperator, ":")
				fval, err := p.parseExpr()
				if err != nil {
					return nil, err
				}
				fields = append(fields, FieldAssign{Name: fname.Value, Value: fval})
				if p.current().Value == "," {
					p.advance()
				} else {
					break
				}
			}
			p.expect(TokenDelimiter, "}")
			return &StructLitExpr{Name: t.Value, Fields: fields, Line: t.Line, Col: t.Col}, nil
		}
		p.advance()
		return &IdentExpr{Name: t.Value, Line: t.Line, Col: t.Col}, nil
	case TokenKeyword:
		switch t.Value {
		case "true", "false":
			p.advance()
			return &BoolLit{Value: t.Value == "true", Line: t.Line, Col: t.Col}, nil
		case "nil":
			p.advance()
			return &NilLit{Line: t.Line, Col: t.Col}, nil
		case "if":
			p.advance()
			cond, err := p.parseExpr()
			if err != nil {
				return nil, err
			}
			then, err := p.parseBlock()
			if err != nil {
				return nil, err
			}
			var els Expr
			if p.current().Type == TokenKeyword && p.current().Value == "else" {
				p.advance()
				els, err = p.parseExpr()
				if err != nil {
					return nil, err
				}
			}
			return &IfExpr{Cond: cond, Then: &BlockExpr{Stmts: then, Line: t.Line, Col: t.Col}, Else: els, Line: t.Line, Col: t.Col}, nil
		}
	case TokenDelimiter:
		if t.Value == "(" {
			p.advance()
			x, err := p.parseExpr()
			if err != nil {
				return nil, err
			}
			p.expect(TokenDelimiter, ")")
			return x, nil
		}
	}
	return nil, fmt.Errorf("unexpected token %s %q at L%d:C%d", t.Type, t.Value, t.Line, t.Col)
}

// BlockExpr wraps statements as an expression (for if expressions).
type BlockExpr struct {
	Stmts []Stmt
	Line  int
	Col   int
}

func (e *BlockExpr) exprNode()      {}
func (e *BlockExpr) String() string { return "{ ... }" }
func (e *BlockExpr) Pos() (int, int) { return e.Line, e.Col }