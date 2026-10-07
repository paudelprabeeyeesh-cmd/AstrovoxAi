package rewrite

import (
	"testing"

	"github.com/astrovox/astrovox/internal/ir"
)

func TestMatcherMatch(t *testing.T) {
	m := NewMatcher()
	g := &ir.Graph{Nodes: map[int64]*ir.Node{1: {Op: "matmul"}}}
	m.AddPattern(&Pattern{Nodes: []*ir.Node{{Op: "matmul"}}})
	results := m.Match(g)
	if len(results) != 1 {
		t.Fatalf("expected 1 match, got %d", len(results))
	}
}

func TestMatcherNoMatch(t *testing.T) {
	m := NewMatcher()
	g := &ir.Graph{Nodes: map[int64]*ir.Node{1: {Op: "add"}}}
	m.AddPattern(&Pattern{Nodes: []*ir.Node{{Op: "matmul"}}})
	results := m.Match(g)
	if len(results) != 0 {
		t.Fatalf("expected 0 matches, got %d", len(results))
	}
}

func TestRuleEngineApply(t *testing.T) {
	e := NewRuleEngine()
	e.AddRule(&RewriteRule{
		Name:    "test",
		Pattern: &Pattern{Nodes: []*ir.Node{{Op: "matmul"}}},
		Replace: func(g *ir.Graph, m MatchResult) []*ir.Node {
			return []*ir.Node{{Op: "linear"}}
		},
	})
	g := &ir.Graph{Nodes: map[int64]*ir.Node{1: {Op: "matmul"}}}
	results := e.Apply(g)
	if len(results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(results))
	}
}

func TestRewriteResult(t *testing.T) {
	r := &RewriteResult{
		Rule:  &RewriteRule{Name: "test"},
		Match: MatchResult{Root: 1},
	}
	if r.Rule.Name != "test" || r.Match.Root != 1 {
		t.Fatal("unexpected result")
	}
}

func TestPatternLibrary(t *testing.T) {
	l := NewPatternLibrary()
	p := &Pattern{Name: "matmul"}
	l.Register("matmul", p)
	if l.Get("matmul") != p {
		t.Fatal("expected same pattern")
	}
	names := l.List()
	if len(names) != 1 {
		t.Fatalf("expected 1 pattern, got %d", len(names))
	}
}

func TestStats(t *testing.T) {
	s := &Stats{}
	s.RecordMatch()
	s.RecordApply()
	if s.Matched != 1 || s.Applied != 1 {
		t.Fatalf("unexpected stats: matched=%d applied=%d", s.Matched, s.Applied)
	}
}

func TestRegisterDefaults(t *testing.T) {
	e := NewRuleEngine()
	RegisterDefaults(e)
	if len(e.rules) != 3 {
		t.Fatalf("expected 3 default rules, got %d", len(e.rules))
	}
}

func TestEdgeStruct(t *testing.T) {
	e := Edge{From: 1, To: 2}
	if e.From != 1 || e.To != 2 {
		t.Fatal("unexpected edge")
	}
}

func TestPatternStruct(t *testing.T) {
	p := Pattern{Name: "test"}
	if p.Name != "test" {
		t.Fatal("unexpected pattern name")
	}
}

func TestMatchResultStruct(t *testing.T) {
	m := MatchResult{Pattern: &Pattern{Name: "test"}, Root: 1}
	if m.Pattern.Name != "test" || m.Root != 1 {
		t.Fatal("unexpected match result")
	}
}
