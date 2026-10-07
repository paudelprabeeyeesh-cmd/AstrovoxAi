package arch

import "testing"

func TestDetectLayerViolationsNone(t *testing.T) {
	g := NewDependencyGraph()
	g.AddPackage("m/cmd/app", "cmd/app", []string{"m/pkg/api"})
	g.AddPackage("m/pkg/api", "pkg/api", []string{"m/internal/engine"})
	g.AddPackage("m/internal/engine", "internal/engine", nil)

	layers := []Layer{
		{Name: "cli", Packages: []string{"m/cmd/", "m/pkg/"}},
		{Name: "internal", Packages: []string{"m/internal/"}},
	}
	if v := DetectLayerViolations(g, layers); len(v) != 0 {
		t.Fatalf("expected no violations, got %v", v)
	}
}

func TestDetectLayerViolationsUpward(t *testing.T) {
	g := NewDependencyGraph()
	g.AddPackage("m/internal/engine", "internal/engine", []string{"m/pkg/api"})
	g.AddPackage("m/pkg/api", "pkg/api", nil)

	layers := []Layer{
		{Name: "cli", Packages: []string{"m/pkg/"}},
		{Name: "internal", Packages: []string{"m/internal/"}},
	}
	v := DetectLayerViolations(g, layers)
	if len(v) != 1 {
		t.Fatalf("expected 1 violation, got %v", v)
	}
	if v[0].From != "m/internal/engine" || v[0].To != "m/pkg/api" || v[0].Rule != "layer" {
		t.Fatalf("unexpected violation: %+v", v[0])
	}
}

func TestDetectLayerViolationsSameLayerAllowed(t *testing.T) {
	g := NewDependencyGraph()
	g.AddPackage("m/pkg/a", "pkg/a", []string{"m/pkg/b"})
	g.AddPackage("m/pkg/b", "pkg/b", nil)

	layers := []Layer{{Name: "cli", Packages: []string{"m/pkg/"}}}
	if v := DetectLayerViolations(g, layers); len(v) != 0 {
		t.Fatalf("same-layer imports allowed, got %v", v)
	}
}

func TestDetectLayerViolationsUnknownPackagesIgnored(t *testing.T) {
	g := NewDependencyGraph()
	g.AddPackage("m/other", "other", []string{"m/pkg/api"})
	g.AddPackage("m/pkg/api", "pkg/api", []string{"m/other"})

	layers := []Layer{{Name: "cli", Packages: []string{"m/pkg/"}}}
	if v := DetectLayerViolations(g, layers); len(v) != 0 {
		t.Fatalf("unmatched packages ignored, got %v", v)
	}
}

func TestDetectLayerViolationsLongestPrefixWins(t *testing.T) {
	g := NewDependencyGraph()
	// m/pkg/legacy sits in the "legacy" layer (longer prefix), not "cli".
	g.AddPackage("m/pkg/legacy/old", "pkg/legacy/old", []string{"m/pkg/new"})
	g.AddPackage("m/pkg/new", "pkg/new", nil)

	layers := []Layer{
		{Name: "legacy", Packages: []string{"m/pkg/legacy/"}},
		{Name: "cli", Packages: []string{"m/pkg/"}},
	}
	// legacy (layer 0) importing cli (layer 1) is downward: allowed.
	if v := DetectLayerViolations(g, layers); len(v) != 0 {
		t.Fatalf("expected longest-prefix match to allow import, got %v", v)
	}
}

func TestDetectLayerViolationsSorted(t *testing.T) {
	g := NewDependencyGraph()
	g.AddPackage("m/internal/b", "internal/b", []string{"m/pkg/z"})
	g.AddPackage("m/internal/a", "internal/a", []string{"m/pkg/z"})
	g.AddPackage("m/pkg/z", "pkg/z", nil)

	layers := []Layer{
		{Name: "cli", Packages: []string{"m/pkg/"}},
		{Name: "internal", Packages: []string{"m/internal/"}},
	}
	v := DetectLayerViolations(g, layers)
	if len(v) != 2 || v[0].From != "m/internal/a" || v[1].From != "m/internal/b" {
		t.Fatalf("violations not sorted: %v", v)
	}
}
