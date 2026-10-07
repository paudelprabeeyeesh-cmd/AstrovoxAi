package arch

import (
	"path/filepath"
	"runtime"
	"testing"
)

func TestAddPackageAndQueries(t *testing.T) {
	g := NewDependencyGraph()
	g.AddPackage("m/a", "a", []string{"m/b", "fmt"})
	g.AddPackage("m/b", "b", nil)

	paths := g.Packages()
	if len(paths) != 2 || paths[0] != "m/a" || paths[1] != "m/b" {
		t.Fatalf("unexpected packages: %v", paths)
	}
	imports := g.Imports("m/a")
	if len(imports) != 2 || imports[0] != "fmt" || imports[1] != "m/b" {
		t.Fatalf("unexpected imports: %v", imports)
	}
	deps := g.Dependents("m/b")
	if len(deps) != 1 || deps[0] != "m/a" {
		t.Fatalf("unexpected dependents: %v", deps)
	}
	if g.Node("m/b").Dir != "b" {
		t.Fatalf("unexpected dir: %v", g.Node("m/b").Dir)
	}
	if g.Node("missing") != nil {
		t.Fatal("expected nil node for missing package")
	}
	if g.Imports("missing") != nil {
		t.Fatal("expected nil imports for missing package")
	}
}

func TestAddPackageIdempotent(t *testing.T) {
	g := NewDependencyGraph()
	g.AddPackage("m/a", "a", []string{"m/b"})
	g.AddPackage("m/a", "a", []string{"m/c"})
	imports := g.Imports("m/a")
	if len(imports) != 1 || imports[0] != "m/c" {
		t.Fatalf("expected latest imports to win, got %v", imports)
	}
}

func TestBuildDependencyGraph(t *testing.T) {
	_, filename, _, _ := runtime.Caller(0)
	root := filepath.Join(filepath.Dir(filename), "..", "..")
	g, err := BuildDependencyGraph(root)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(g.Packages()) < 10 {
		t.Fatalf("expected many packages, got %d", len(g.Packages()))
	}
	if g.Node("github.com/astrovox/astrovox/tensor") == nil {
		t.Fatal("expected tensor package in graph")
	}
}

func TestBuildDependencyGraphMissingGoMod(t *testing.T) {
	g, err := BuildDependencyGraph(t.TempDir())
	if err == nil {
		t.Fatal("expected error for missing go.mod")
	}
	if g != nil {
		t.Fatal("expected nil graph on error")
	}
}

func TestModulePath(t *testing.T) {
	dir := t.TempDir()
	if err := writeFile(filepath.Join(dir, "go.mod"), "module example.com/m\n\ngo 1.27\n"); err != nil {
		t.Fatalf("write go.mod: %v", err)
	}
	got, err := modulePath(dir)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got != "example.com/m" {
		t.Fatalf("modulePath = %q, want example.com/m", got)
	}
}

func TestBuildDependencyGraphSkipsHiddenAndTestdata(t *testing.T) {
	dir := t.TempDir()
	if err := writeFile(filepath.Join(dir, "go.mod"), "module example.com/m\n"); err != nil {
		t.Fatalf("write go.mod: %v", err)
	}
	hidden := filepath.Join(dir, ".hidden")
	if err := mkdir(hidden); err != nil {
		t.Fatalf("mkdir: %v", err)
	}
	if err := writeFile(filepath.Join(hidden, "x.go"), "package hidden\n"); err != nil {
		t.Fatalf("write: %v", err)
	}
	testdata := filepath.Join(dir, "testdata")
	if err := mkdir(testdata); err != nil {
		t.Fatalf("mkdir: %v", err)
	}
	if err := writeFile(filepath.Join(testdata, "x.go"), "package testdata\n"); err != nil {
		t.Fatalf("write: %v", err)
	}
	g, err := BuildDependencyGraph(dir)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	for _, p := range g.Packages() {
		if p == "example.com/m/.hidden" || p == "example.com/m/testdata" {
			t.Fatalf("expected skipped dirs to be absent, got %v", p)
		}
	}
}
