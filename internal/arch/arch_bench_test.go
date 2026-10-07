package arch

import (
	"path/filepath"
	"runtime"
	"testing"
)

func BenchmarkBuildDependencyGraph(b *testing.B) {
	_, filename, _, _ := runtime.Caller(0)
	root := filepath.Join(filepath.Dir(filename), "..", "..")
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		g, err := BuildDependencyGraph(root)
		if err != nil {
			b.Fatalf("unexpected error: %v", err)
		}
		if len(g.Packages()) == 0 {
			b.Fatal("expected packages")
		}
	}
}

func benchmarkCycleGraph(size int) *DependencyGraph {
	g := NewDependencyGraph()
	for i := 0; i < size; i++ {
		imports := []string{}
		if i > 0 {
			imports = append(imports, itoa(i-1))
		}
		g.AddPackage("m/p"+itoa(i), "p"+itoa(i), imports)
	}
	return g
}

func itoa(i int) string {
	if i == 0 {
		return "0"
	}
	var digits []byte
	for i > 0 {
		digits = append([]byte{byte('0' + i%10)}, digits...)
		i /= 10
	}
	return string(digits)
}

func BenchmarkFindImportCyclesLinear(b *testing.B) {
	g := benchmarkCycleGraph(200)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = g.FindImportCycles()
	}
}

func BenchmarkFindImportCyclesCyclic(b *testing.B) {
	g := benchmarkCycleGraph(200)
	g.AddPackage("m/p199", "p199", []string{"m/p0"})
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = g.FindImportCycles()
	}
}

func BenchmarkDetectLayerViolations(b *testing.B) {
	g := NewDependencyGraph()
	for i := 0; i < 100; i++ {
		g.AddPackage("m/internal/p"+itoa(i), "p"+itoa(i), []string{"m/pkg/api"})
	}
	g.AddPackage("m/pkg/api", "api", nil)
	layers := []Layer{
		{Name: "cli", Packages: []string{"m/pkg/"}},
		{Name: "internal", Packages: []string{"m/internal/"}},
	}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = DetectLayerViolations(g, layers)
	}
}

func BenchmarkValidateDependencies(b *testing.B) {
	g := NewDependencyGraph()
	for i := 0; i < 100; i++ {
		g.AddPackage("m/pkg/p"+itoa(i), "p"+itoa(i), []string{"m/internal/x", "fmt"})
	}
	g.AddPackage("m/internal/x", "x", nil)
	rules := []Rule{{From: "m/pkg/", Allow: []string{"m/internal/", "fmt"}}}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = ValidateDependencies(g, rules)
	}
}
