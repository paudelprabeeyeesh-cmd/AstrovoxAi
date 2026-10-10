package rewrite

import "github.com/astrovox/astrovox/internal/ir"

// Pattern represents a graph pattern to match.
type Pattern struct {
	Name  string
	Nodes []*ir.Node
	Edges []Edge
	Attrs map[string]interface{}
}

// Edge represents a directed edge in a pattern.
type Edge struct {
	From int64
	To   int64
}

// Matcher matches patterns in a graph.
type Matcher struct {
	patterns []*Pattern
}

// NewMatcher creates a new matcher.
func NewMatcher() *Matcher {
	return &Matcher{}
}

// AddPattern registers a pattern.
func (m *Matcher) AddPattern(p *Pattern) {
	m.patterns = append(m.patterns, p)
}

// Match searches for patterns in the graph.
func (m *Matcher) Match(g *ir.Graph) []MatchResult {
	var results []MatchResult
	for _, p := range m.patterns {
		results = append(results, m.matchPattern(g, p)...)
	}
	return results
}

func (m *Matcher) matchPattern(g *ir.Graph, p *Pattern) []MatchResult {
	var results []MatchResult
	for _, n := range g.Nodes {
		if n.Op == p.Nodes[0].Op {
			results = append(results, MatchResult{Pattern: p, Root: n.ID})
		}
	}
	return results
}

// MatchResult represents a successful pattern match.
type MatchResult struct {
	Pattern *Pattern
	Root    int64
}

// RewriteRule defines a graph rewrite rule.
type RewriteRule struct {
	Name     string
	Pattern  *Pattern
	Replace  func(*ir.Graph, MatchResult) []*ir.Node
	Priority int
}

// RuleEngine applies rewrite rules to a graph.
type RuleEngine struct {
	rules []*RewriteRule
}

// NewRuleEngine creates a new engine.
func NewRuleEngine() *RuleEngine {
	return &RuleEngine{}
}

// AddRule registers a rewrite rule.
func (e *RuleEngine) AddRule(r *RewriteRule) {
	e.rules = append(e.rules, r)
}

// Apply applies all rules to the graph.
func (e *RuleEngine) Apply(g *ir.Graph) []*RewriteResult {
	var results []*RewriteResult
	for _, r := range e.rules {
		matcher := NewMatcher()
		matcher.AddPattern(r.Pattern)
		matches := matcher.Match(g)
		for _, m := range matches {
			replacement := r.Replace(g, m)
			results = append(results, &RewriteResult{
				Rule:        r,
				Match:       m,
				Replacement: replacement,
			})
		}
	}
	return results
}

// RewriteResult records a rewrite application.
type RewriteResult struct {
	Rule        *RewriteRule
	Match       MatchResult
	Replacement []*ir.Node
}

// Stats tracks rewrite statistics.
type Stats struct {
	Applied int
	Matched int
}

// RecordMatch increments match count.
func (s *Stats) RecordMatch() { s.Matched++ }

// RecordApply increments apply count.
func (s *Stats) RecordApply() { s.Applied++ }
