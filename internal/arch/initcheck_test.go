package arch

import (
	"os"
	"path/filepath"
	"testing"
)

func TestCheckModuleInitClean(t *testing.T) {
	dir := t.TempDir()
	if err := writeFile(filepath.Join(dir, "go.mod"), "module example.com/m\n"); err != nil {
		t.Fatalf("write go.mod: %v", err)
	}
	pkg := filepath.Join(dir, "a")
	if err := os.MkdirAll(pkg, 0755); err != nil {
		t.Fatalf("mkdir: %v", err)
	}
	if err := writeFile(filepath.Join(pkg, "a.go"), "package a\n\nfunc init() {\n\t_ = 1\n}\n"); err != nil {
		t.Fatalf("write: %v", err)
	}
	if issues := CheckModuleInit(dir); len(issues) != 0 {
		t.Fatalf("expected no issues, got %v", issues)
	}
}

func TestCheckModuleInitMissingGoMod(t *testing.T) {
	issues := CheckModuleInit(t.TempDir())
	if len(issues) != 1 || issues[0].Message == "" {
		t.Fatalf("expected go.mod issue, got %v", issues)
	}
}

func TestCheckModuleInitInconsistentPackage(t *testing.T) {
	dir := t.TempDir()
	if err := writeFile(filepath.Join(dir, "go.mod"), "module example.com/m\n"); err != nil {
		t.Fatalf("write go.mod: %v", err)
	}
	pkg := filepath.Join(dir, "a")
	if err := os.MkdirAll(pkg, 0755); err != nil {
		t.Fatalf("mkdir: %v", err)
	}
	if err := writeFile(filepath.Join(pkg, "a.go"), "package a\n"); err != nil {
		t.Fatalf("write: %v", err)
	}
	if err := writeFile(filepath.Join(pkg, "b.go"), "package b\n"); err != nil {
		t.Fatalf("write: %v", err)
	}
	issues := CheckModuleInit(dir)
	if len(issues) == 0 {
		t.Fatal("expected inconsistent package name issue")
	}
	found := false
	for _, issue := range issues {
		if issue.Message == "inconsistent package name b (expected a)" {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected inconsistency issue, got %v", issues)
	}
}

func TestCheckModuleInitOsExit(t *testing.T) {
	dir := t.TempDir()
	if err := writeFile(filepath.Join(dir, "go.mod"), "module example.com/m\n"); err != nil {
		t.Fatalf("write go.mod: %v", err)
	}
	pkg := filepath.Join(dir, "a")
	if err := os.MkdirAll(pkg, 0755); err != nil {
		t.Fatalf("mkdir: %v", err)
	}
	src := "package a\n\nimport \"os\"\n\nfunc init() {\n\tos.Exit(1)\n}\n"
	if err := writeFile(filepath.Join(pkg, "a.go"), src); err != nil {
		t.Fatalf("write: %v", err)
	}
	issues := CheckModuleInit(dir)
	found := false
	for _, issue := range issues {
		if issue.Message == "init function calls os.Exit" {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected os.Exit issue, got %v", issues)
	}
}

func TestCheckModuleInitTestFileAllowed(t *testing.T) {
	dir := t.TempDir()
	if err := writeFile(filepath.Join(dir, "go.mod"), "module example.com/m\n"); err != nil {
		t.Fatalf("write go.mod: %v", err)
	}
	pkg := filepath.Join(dir, "a")
	if err := os.MkdirAll(pkg, 0755); err != nil {
		t.Fatalf("mkdir: %v", err)
	}
	if err := writeFile(filepath.Join(pkg, "a.go"), "package a\n"); err != nil {
		t.Fatalf("write: %v", err)
	}
	if err := writeFile(filepath.Join(pkg, "a_test.go"), "package a_test\n"); err != nil {
		t.Fatalf("write: %v", err)
	}
	if issues := CheckModuleInit(dir); len(issues) != 0 {
		t.Fatalf("expected _test package name to be allowed, got %v", issues)
	}
}
