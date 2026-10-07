package arch

import "testing"

func TestFindImportCyclesNone(t *testing.T) {
	g := NewDependencyGraph()
	g.AddPackage("m/a", "a", []string{"m/b"})
	g.AddPackage("m/b", "b", []string{"m/c"})
	g.AddPackage("m/c", "c", nil)
	if cycles := g.FindImportCycles(); len(cycles) != 0 {
		t.Fatalf("expected no cycles, got %v", cycles)
	}
}

func TestFindImportCyclesSimple(t *testing.T) {
	g := NewDependencyGraph()
	g.AddPackage("m/a", "a", []string{"m/b"})
	g.AddPackage("m/b", "b", []string{"m/c"})
	g.AddPackage("m/c", "c", []string{"m/a"})
	cycles := g.FindImportCycles()
	if len(cycles) != 1 {
		t.Fatalf("expected 1 cycle, got %v", cycles)
	}
	want := []string{"m/a", "m/b", "m/c"}
	if len(cycles[0]) != len(want) {
		t.Fatalf("cycle = %v, want %v", cycles[0], want)
	}
	for i := range want {
		if cycles[0][i] != want[i] {
			t.Fatalf("cycle = %v, want %v", cycles[0], want)
		}
	}
}

func TestFindImportCyclesSelfLoopIgnored(t *testing.T) {
	g := NewDependencyGraph()
	g.AddPackage("m/a", "a", []string{"m/a"})
	if cycles := g.FindImportCycles(); len(cycles) != 0 {
		t.Fatalf("self-loop is not a multi-node cycle, got %v", cycles)
	}
}

func TestFindImportCyclesTwoComponents(t *testing.T) {
	g := NewDependencyGraph()
	g.AddPackage("m/a", "a", []string{"m/b"})
	g.AddPackage("m/b", "b", []string{"m/a"})
	g.AddPackage("m/x", "x", []string{"m/y"})
	g.AddPackage("m/y", "y", []string{"m/x"})
	cycles := g.FindImportCycles()
	if len(cycles) != 2 {
		t.Fatalf("expected 2 cycles, got %v", cycles)
	}
	if cycles[0][0] != "m/a" || cycles[1][0] != "m/x" {
		t.Fatalf("cycles not sorted: %v", cycles)
	}
}

func TestFindImportCyclesExternalImportsIgnored(t *testing.T) {
	g := NewDependencyGraph()
	g.AddPackage("m/a", "a", []string{"fmt"})
	g.AddPackage("m/b", "b", []string{"m/a", "fmt"})
	if cycles := g.FindImportCycles(); len(cycles) != 0 {
		t.Fatalf("external imports must not form cycles, got %v", cycles)
	}
}

func TestFindImportCyclesDiamond(t *testing.T) {
	g := NewDependencyGraph()
	g.AddPackage("m/a", "a", []string{"m/b", "m/c"})
	g.AddPackage("m/b", "b", []string{"m/d"})
	g.AddPackage("m/c", "c", []string{"m/d"})
	g.AddPackage("m/d", "d", nil)
	if cycles := g.FindImportCycles(); len(cycles) != 0 {
		t.Fatalf("diamond has no cycle, got %v", cycles)
	}
}
