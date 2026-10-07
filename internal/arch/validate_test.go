package arch

import "testing"

func TestValidateDependenciesPass(t *testing.T) {
	g := NewDependencyGraph()
	g.AddPackage("m/pkg/a", "pkg/a", []string{"m/internal/x", "fmt"})
	g.AddPackage("m/internal/x", "internal/x", nil)

	rules := []Rule{
		{From: "m/pkg/", Allow: []string{"m/internal/", "fmt"}},
	}
	if v := ValidateDependencies(g, rules); len(v) != 0 {
		t.Fatalf("expected no violations, got %v", v)
	}
}

func TestValidateDependenciesDeny(t *testing.T) {
	g := NewDependencyGraph()
	g.AddPackage("m/pkg/a", "pkg/a", []string{"m/pkg/b"})
	g.AddPackage("m/pkg/b", "pkg/b", nil)

	rules := []Rule{
		{From: "m/pkg/", Deny: []string{"m/pkg/b"}},
	}
	v := ValidateDependencies(g, rules)
	if len(v) != 1 || v[0].Rule != "deny" || v[0].To != "m/pkg/b" {
		t.Fatalf("unexpected violations: %v", v)
	}
}

func TestValidateDependenciesAllowList(t *testing.T) {
	g := NewDependencyGraph()
	g.AddPackage("m/pkg/a", "pkg/a", []string{"m/other/b"})
	g.AddPackage("m/other/b", "other/b", nil)

	rules := []Rule{
		{From: "m/pkg/", Allow: []string{"m/internal/"}},
	}
	v := ValidateDependencies(g, rules)
	if len(v) != 1 || v[0].Rule != "allow" {
		t.Fatalf("expected allow violation, got %v", v)
	}
}

func TestValidateDependenciesNoRule(t *testing.T) {
	g := NewDependencyGraph()
	g.AddPackage("m/other/a", "other/a", []string{"m/other/b"})
	g.AddPackage("m/other/b", "other/b", nil)

	rules := []Rule{{From: "m/pkg/", Allow: []string{"m/internal/"}}}
	if v := ValidateDependencies(g, rules); len(v) != 0 {
		t.Fatalf("packages without rules are unconstrained, got %v", v)
	}
}

func TestValidateDependenciesLongestPrefixWins(t *testing.T) {
	g := NewDependencyGraph()
	g.AddPackage("m/pkg/legacy/a", "pkg/legacy/a", []string{"m/pkg/b"})
	g.AddPackage("m/pkg/b", "pkg/b", nil)

	rules := []Rule{
		{From: "m/pkg/", Allow: []string{"m/internal/"}},
		{From: "m/pkg/legacy/", Allow: []string{"m/pkg/"}},
	}
	if v := ValidateDependencies(g, rules); len(v) != 0 {
		t.Fatalf("expected legacy rule to apply, got %v", v)
	}
}

func TestValidateDependenciesSorted(t *testing.T) {
	g := NewDependencyGraph()
	g.AddPackage("m/pkg/a", "pkg/a", []string{"m/x", "m/y"})
	g.AddPackage("m/x", "x", nil)
	g.AddPackage("m/y", "y", nil)

	rules := []Rule{{From: "m/pkg/", Deny: []string{"m/"}}}
	v := ValidateDependencies(g, rules)
	if len(v) != 2 || v[0].To != "m/x" || v[1].To != "m/y" {
		t.Fatalf("violations not sorted: %v", v)
	}
}
