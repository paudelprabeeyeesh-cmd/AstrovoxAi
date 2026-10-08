package rewrite

import (
	"testing"

	"github.com/astrovox/astrovox/internal/ir"
)

func TestMatcher_NoPatterns(t *testing.T) {
	m := NewMatcher()
	g := &ir.Graph{Nodes: map[int64]*ir.Node{0: {Op: "add"}}}
	if len(m.Match(g)) != 0 {
		t.Fatal("expected no matches without patterns")
	}
}

func TestMatcher_SinglePattern(t *testing.T) {
	m := NewMatcher()
	m.AddPattern(&Pattern{Nodes: []*ir.Node{{Op: "matmul"}}})
	g := &ir.Graph{Nodes: map[int64]*ir.Node{0: {Op: "matmul"}, 1: {Op: "add"}}}
	matches := m.Match(g)
	if len(matches) != 1 {
		t.Fatalf("matches = %d, want 1", len(matches))
	}
	if matches[0].Root != 0 {
		t.Fatalf("root = %d, want 0", matches[0].Root)
	}
}

func TestMatcher_MultipleMatches(t *testing.T) {
	m := NewMatcher()
	m.AddPattern(&Pattern{Nodes: []*ir.Node{{Op: "relu"}}})
	g := &ir.Graph{Nodes: map[int64]*ir.Node{
		0: {Op: "add"},
		1: {Op: "relu"},
		2: {Op: "relu"},
	}}
	if len(m.Match(g)) != 2 {
		t.Fatalf("matches = %d, want 2", len(m.Match(g)))
	}
}

func TestMatcher_MultiplePatterns(t *testing.T) {
	m := NewMatcher()
	m.AddPattern(&Pattern{Nodes: []*ir.Node{{Op: "add"}}})
	m.AddPattern(&Pattern{Nodes: []*ir.Node{{Op: "mul"}}})
	g := &ir.Graph{Nodes: map[int64]*ir.Node{
		0: {Op: "add"},
		1: {Op: "mul"},
	}}
	if len(m.Match(g)) != 2 {
		t.Fatalf("matches = %d, want 2", len(m.Match(g)))
	}
}

func TestMatcher_EmptyGraph(t *testing.T) {
	m := NewMatcher()
	m.AddPattern(&Pattern{Nodes: []*ir.Node{{Op: "add"}}})
	if len(m.Match(&ir.Graph{})) != 0 {
		t.Fatal("expected no matches on empty graph")
	}
}

func TestRuleEngine_NoRules(t *testing.T) {
	e := NewRuleEngine()
	g := &ir.Graph{Nodes: map[int64]*ir.Node{0: {Op: "add"}}}
	if len(e.Apply(g)) != 0 {
		t.Fatal("expected no results without rules")
	}
}

func TestRuleEngine_SingleRule(t *testing.T) {
	e := NewRuleEngine()
	e.AddRule(&RewriteRule{
		Name:    "add_linear",
		Pattern: &Pattern{Nodes: []*ir.Node{{Op: "add"}}},
		Replace: func(g *ir.Graph, m MatchResult) []*ir.Node {
			return []*ir.Node{{Op: "linear"}}
		},
	})
	g := &ir.Graph{Nodes: map[int64]*ir.Node{0: {Op: "add"}}}
	results := e.Apply(g)
	if len(results) != 1 {
		t.Fatalf("results = %d, want 1", len(results))
	}
	if results[0].Rule.Name != "add_linear" {
		t.Fatalf("rule = %s, want add_linear", results[0].Rule.Name)
	}
}

func TestRuleEngine_MultipleRules(t *testing.T) {
	e := NewRuleEngine()
	e.AddRule(&RewriteRule{
		Name:    "add_rule",
		Pattern: &Pattern{Nodes: []*ir.Node{{Op: "add"}}},
		Replace: func(g *ir.Graph, m MatchResult) []*ir.Node {
			return []*ir.Node{{Op: "linear"}}
		},
	})
	e.AddRule(&RewriteRule{
		Name:    "mul_rule",
		Pattern: &Pattern{Nodes: []*ir.Node{{Op: "mul"}}},
		Replace: func(g *ir.Graph, m MatchResult) []*ir.Node {
			return []*ir.Node{{Op: "linear"}}
		},
	})
	g := &ir.Graph{Nodes: map[int64]*ir.Node{0: {Op: "add"}, 1: {Op: "mul"}}}
	results := e.Apply(g)
	if len(results) != 2 {
		t.Fatalf("results = %d, want 2", len(results))
	}
}

func TestRuleEngine_NoMatch(t *testing.T) {
	e := NewRuleEngine()
	e.AddRule(&RewriteRule{
		Name:    "matmul_rule",
		Pattern: &Pattern{Nodes: []*ir.Node{{Op: "matmul"}}},
		Replace: func(g *ir.Graph, m MatchResult) []*ir.Node { return nil },
	})
	g := &ir.Graph{Nodes: map[int64]*ir.Node{0: {Op: "add"}}}
	if len(e.Apply(g)) != 0 {
		t.Fatal("expected no results")
	}
}

func TestPatternLibrary_GetMissing(t *testing.T) {
	l := NewPatternLibrary()
	if l.Get("missing") != nil {
		t.Fatal("expected nil for missing pattern")
	}
}

func TestPatternLibrary_ListEmpty(t *testing.T) {
	l := NewPatternLibrary()
	if names := l.List(); len(names) != 0 {
		t.Fatalf("len = %d, want 0", len(names))
	}
}

func TestPatternLibrary_Overwrite(t *testing.T) {
	l := NewPatternLibrary()
	l.Register("p", &Pattern{Name: "v1"})
	l.Register("p", &Pattern{Name: "v2"})
	if got := l.Get("p").Name; got != "v2" {
		t.Fatalf("overwrite: got %s, want v2", got)
	}
}

func TestPattern_Struct(t *testing.T) {
	p := &Pattern{
		Name:  "p1",
		Nodes: []*ir.Node{{Op: "add"}},
		Edges: []Edge{{From: 0, To: 1}},
		Attrs: map[string]interface{}{"key": "val"},
	}
	if p.Name != "p1" {
		t.Fatalf("Name = %s, want p1", p.Name)
	}
	if len(p.Nodes) != 1 {
		t.Fatalf("Nodes len = %d, want 1", len(p.Nodes))
	}
	if len(p.Edges) != 1 {
		t.Fatalf("Edges len = %d, want 1", len(p.Edges))
	}
	if p.Attrs["key"] != "val" {
		t.Fatal("Attrs mismatch")
	}
}

func TestRewriteResult_Struct(t *testing.T) {
	rr := &RewriteResult{
		Rule:       &RewriteRule{Name: "r1"},
		Match:      MatchResult{Root: 1},
		Replacement: []*ir.Node{{Op: "linear"}},
	}
	if rr.Rule.Name != "r1" {
		t.Fatalf("Rule.Name = %s, want r1", rr.Rule.Name)
	}
	if rr.Match.Root != 1 {
		t.Fatalf("Match.Root = %d, want 1", rr.Match.Root)
	}
	if len(rr.Replacement) != 1 {
		t.Fatalf("Replacement len = %d, want 1", len(rr.Replacement))
	}
}

func TestRewriteRule_Struct(t *testing.T) {
	rule := &RewriteRule{
		Name:     "test_rule",
		Pattern:  &Pattern{Name: "pat"},
		Replace:  nil,
		Priority: 100,
	}
	if rule.Name != "test_rule" {
		t.Fatalf("Name = %s, want test_rule", rule.Name)
	}
	if rule.Priority != 100 {
		t.Fatalf("Priority = %d, want 100", rule.Priority)
	}
}
