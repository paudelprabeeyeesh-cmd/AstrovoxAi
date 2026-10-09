// Package lang implements a mini programming language with a full
// compiler pipeline: lexer, parser, AST, optimizer, and code generator.
package lang

import (
	"fmt"
	"strings"
	"unicode"
)

// TokenType identifies the type of a lexical token.
type TokenType int

const (
	TokenEOF TokenType = iota
	TokenNewline
	TokenIdent
	TokenInt
	TokenFloat
	TokenString
	TokenKeyword
	TokenOperator
	TokenDelimiter
	TokenComment
)

func (t TokenType) String() string {
	switch t {
	case TokenEOF:
		return "EOF"
	case TokenNewline:
		return "NEWLINE"
	case TokenIdent:
		return "IDENT"
	case TokenInt:
		return "INT"
	case TokenFloat:
		return "FLOAT"
	case TokenString:
		return "STRING"
	case TokenKeyword:
		return "KEYWORD"
	case TokenOperator:
		return "OPERATOR"
	case TokenDelimiter:
		return "DELIMITER"
	case TokenComment:
		return "COMMENT"
	default:
		return "UNKNOWN"
	}
}

// Token represents a lexical token.
type Token struct {
	Type   TokenType
	Value  string
	Line   int
	Col int
}

func (t Token) String() string {
	return fmt.Sprintf("Token(%s, %q, L%d:C%d)", t.Type, t.Value, t.Line, t.Col)
}

// keywords of the mini language.
var keywords = map[string]bool{
	"fn": true, "let": true, "mut": true, "if": true, "else": true,
	"while": true, "for": true, "in": true, "return": true, "break": true,
	"continue": true, "struct": true, "true": true, "false": true,
	"nil": true, "import": true, "export": true, "as": true,
	"match": true, "enum": true, "impl": true, "self": true,
}

// Lexer tokenizes source code.
type Lexer struct {
	input  string
	pos    int
	line   int
	col    int
	tokens []Token
	errors []string
}

// NewLexer creates a new lexer.
func NewLexer(input string) *Lexer {
	return &Lexer{input: input, line: 1, col: 1}
}

// Lex tokenizes the entire input.
func (lx *Lexer) Lex() ([]Token, error) {
	for lx.pos < len(lx.input) {
		ch := lx.input[lx.pos]

		// Skip whitespace (but track newlines)
		if ch == ' ' || ch == '\t' || ch == '\r' {
			lx.advance()
			continue
		}
		if ch == '\n' {
			lx.tokens = append(lx.tokens, Token{Type: TokenNewline, Value: "\\n", Line: lx.line, Col: lx.col})
			lx.advance()
			continue
		}

		// Comments
		if ch == '/' && lx.pos+1 < len(lx.input) && lx.input[lx.pos+1] == '/' {
			lx.lexLineComment()
			continue
		}
		if ch == '/' && lx.pos+1 < len(lx.input) && lx.input[lx.pos+1] == '*' {
			lx.lexBlockComment()
			continue
		}

		// Strings
		if ch == '"' {
			lx.lexString()
			continue
		}

		// Numbers
		if unicode.IsDigit(rune(ch)) {
			lx.lexNumber()
			continue
		}

		// Identifiers and keywords
		if isIdentStart(ch) {
			lx.lexIdent()
			continue
		}

		// Operators (multi-char first)
		if lx.lexOperator() {
			continue
		}

		// Delimiters
		if isDelimiter(ch) {
			lx.tokens = append(lx.tokens, Token{Type: TokenDelimiter, Value: string(ch), Line: lx.line, Col: lx.col})
			lx.advance()
			continue
		}

		lx.errors = append(lx.errors, fmt.Sprintf("unexpected character %q at L%d:C%d", string(ch), lx.line, lx.col))
		lx.advance()
	}

	lx.tokens = append(lx.tokens, Token{Type: TokenEOF, Line: lx.line, Col: lx.col})

	if len(lx.errors) > 0 {
		return nil, fmt.Errorf("lexer errors: %s", strings.Join(lx.errors, "; "))
	}
	return lx.tokens, nil
}

func (lx *Lexer) advance() {
	if lx.pos < len(lx.input) {
		if lx.input[lx.pos] == '\n' {
			lx.line++
			lx.col = 1
		} else {
			lx.col++
		}
		lx.pos++
	}
}

func (lx *Lexer) peek() byte {
	if lx.pos+1 < len(lx.input) {
		return lx.input[lx.pos+1]
	}
	return 0
}

func (lx *Lexer) lexLineComment() {
	start := lx.pos
	for lx.pos < len(lx.input) && lx.input[lx.pos] != '\n' {
		lx.advance()
	}
	lx.tokens = append(lx.tokens, Token{
		Type: TokenComment, Value: lx.input[start:lx.pos], Line: lx.line, Col: lx.col,
	})
}

func (lx *Lexer) lexBlockComment() {
	start := lx.pos
	lx.advance() // /
	lx.advance() // *
	for lx.pos+1 < len(lx.input) && !(lx.input[lx.pos] == '*' && lx.input[lx.pos+1] == '/') {
		lx.advance()
	}
	if lx.pos+1 < len(lx.input) {
		lx.advance() // *
		lx.advance() // /
	} else {
		lx.errors = append(lx.errors, "unterminated block comment")
	}
	lx.tokens = append(lx.tokens, Token{
		Type: TokenComment, Value: lx.input[start:lx.pos], Line: lx.line, Col: lx.col,
	})
}

func (lx *Lexer) lexString() {
	start := lx.pos
	lx.advance() // opening quote
	var sb strings.Builder
	for lx.pos < len(lx.input) && lx.input[lx.pos] != '"' {
		if lx.input[lx.pos] == '\\' && lx.pos+1 < len(lx.input) {
			lx.advance()
			switch lx.input[lx.pos] {
			case 'n':
				sb.WriteByte('\n')
			case 't':
				sb.WriteByte('\t')
			case 'r':
				sb.WriteByte('\r')
			case '\\':
				sb.WriteByte('\\')
			case '"':
				sb.WriteByte('"')
			case '0':
				sb.WriteByte(0)
			default:
				sb.WriteByte(lx.input[lx.pos])
			}
			lx.advance()
		} else {
			sb.WriteByte(lx.input[lx.pos])
			lx.advance()
		}
	}
	if lx.pos >= len(lx.input) {
		lx.errors = append(lx.errors, "unterminated string literal")
		return
	}
	lx.advance() // closing quote
	_ = start
	lx.tokens = append(lx.tokens, Token{Type: TokenString, Value: sb.String(), Line: lx.line, Col: lx.col})
}

func (lx *Lexer) lexNumber() {
	start := lx.pos
	isFloat := false
	for lx.pos < len(lx.input) {
		ch := lx.input[lx.pos]
		if unicode.IsDigit(rune(ch)) {
			lx.advance()
		} else if ch == '.' && lx.peek() != '.' && !isFloat {
			// Only treat as float if next char is a digit
			if lx.pos+1 < len(lx.input) && unicode.IsDigit(rune(lx.input[lx.pos+1])) {
				isFloat = true
				lx.advance()
			} else {
				break
			}
		} else if ch == 'e' || ch == 'E' {
			isFloat = true
			lx.advance()
			if lx.pos < len(lx.input) && (lx.input[lx.pos] == '+' || lx.input[lx.pos] == '-') {
				lx.advance()
			}
		} else if ch == 'x' || ch == 'X' || (ch >= 'a' && ch <= 'f') || (ch >= 'A' && ch <= 'F') {
			lx.advance()
		} else {
			break
		}
	}
	val := lx.input[start:lx.pos]
	tokType := TokenInt
	if isFloat {
		tokType = TokenFloat
	}
	lx.tokens = append(lx.tokens, Token{Type: tokType, Value: val, Line: lx.line, Col: lx.col})
}

func (lx *Lexer) lexIdent() {
	start := lx.pos
	for lx.pos < len(lx.input) && isIdentChar(lx.input[lx.pos]) {
		lx.advance()
	}
	val := lx.input[start:lx.pos]
	tokType := TokenIdent
	if keywords[val] {
		tokType = TokenKeyword
	}
	lx.tokens = append(lx.tokens, Token{Type: tokType, Value: val, Line: lx.line, Col: lx.col})
}

func (lx *Lexer) lexOperator() bool {
	twoChar := ""
	if lx.pos+1 < len(lx.input) {
		twoChar = lx.input[lx.pos : lx.pos+2]
	}
	multiOps := []string{"==", "!=", "<=", ">=", "&&", "||", "->", "=>", "..", "+=", "-=", "*=", "/="}
	for _, op := range multiOps {
		if twoChar == op {
			lx.tokens = append(lx.tokens, Token{Type: TokenOperator, Value: op, Line: lx.line, Col: lx.col})
			lx.advance()
			lx.advance()
			return true
		}
	}
	singleOps := "+-*/%=<>!&|^~?:."
	if strings.ContainsRune(singleOps, rune(lx.input[lx.pos])) {
		lx.tokens = append(lx.tokens, Token{Type: TokenOperator, Value: string(lx.input[lx.pos]), Line: lx.line, Col: lx.col})
		lx.advance()
		return true
	}
	return false
}

func isIdentStart(ch byte) bool {
	return ch == '_' || (ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z')
}

func isIdentChar(ch byte) bool {
	return isIdentStart(ch) || (ch >= '0' && ch <= '9')
}

func isDelimiter(ch byte) bool {
	return strings.ContainsRune("()[]{},;", rune(ch))
}

// isTypeName reports whether an identifier looks like a type name
// (starts with an uppercase letter). Used by the parser to tell a
// struct literal (`Point { x: 1 }`) apart from a block that follows
// an expression (`if x { ... }`).
func isTypeName(name string) bool {
	return len(name) > 0 && name[0] >= 'A' && name[0] <= 'Z'
}