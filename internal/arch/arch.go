package arch

import (
	"go/parser"
	"go/token"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// PackageNode describes a Go package and its imports.
type PackageNode struct {
	Path    string
	Dir     string
	Imports []string
}

// DependencyGraph is a directed graph of package dependencies within a module.
type DependencyGraph struct {
	nodes map[string]*PackageNode
	edges map[string]map[string]struct{}
}

// NewDependencyGraph creates an empty dependency graph.
func NewDependencyGraph() *DependencyGraph {
	return &DependencyGraph{
		nodes: make(map[string]*PackageNode),
		edges: make(map[string]map[string]struct{}),
	}
}

// AddPackage registers a package and its imports.
func (g *DependencyGraph) AddPackage(path, dir string, imports []string) {
	node, ok := g.nodes[path]
	if !ok {
		node = &PackageNode{Path: path, Dir: dir}
		g.nodes[path] = node
	}
	node.Imports = append([]string(nil), imports...)
	sort.Strings(node.Imports)
	edges, ok := g.edges[path]
	if !ok {
		edges = make(map[string]struct{})
		g.edges[path] = edges
	}
	for _, imp := range imports {
		edges[imp] = struct{}{}
	}
}

// Packages returns all package paths in sorted order.
func (g *DependencyGraph) Packages() []string {
	paths := make([]string, 0, len(g.nodes))
	for path := range g.nodes {
		paths = append(paths, path)
	}
	sort.Strings(paths)
	return paths
}

// Node returns the package node for path, or nil.
func (g *DependencyGraph) Node(path string) *PackageNode {
	return g.nodes[path]
}

// Imports returns the sorted imports of a package.
func (g *DependencyGraph) Imports(path string) []string {
	node := g.nodes[path]
	if node == nil {
		return nil
	}
	return append([]string(nil), node.Imports...)
}

// Dependents returns sorted paths of packages that import path.
func (g *DependencyGraph) Dependents(path string) []string {
	var result []string
	for from, edges := range g.edges {
		if _, ok := edges[path]; ok {
			result = append(result, from)
		}
	}
	sort.Strings(result)
	return result
}

// BuildDependencyGraph walks root, parses Go sources, and builds the
// module's package dependency graph. Non-module imports are included as
// edge targets but are not package nodes.
func BuildDependencyGraph(root string) (*DependencyGraph, error) {
	modulePath, err := modulePath(root)
	if err != nil {
		return nil, err
	}
	g := NewDependencyGraph()
	err = filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if !d.IsDir() {
			return nil
		}
		if path != root {
			name := d.Name()
			if strings.HasPrefix(name, ".") || name == "_" || name == "testdata" {
				return fs.SkipDir
			}
		}
		return addPackageDir(g, root, path, modulePath)
	})
	if err != nil {
		return nil, err
	}
	return g, nil
}

func addPackageDir(g *DependencyGraph, root, dir, modulePath string) error {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return err
	}
	importSet := make(map[string]struct{})
	hasGo := false
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".go") {
			continue
		}
		hasGo = true
		fset := token.NewFileSet()
		file, err := parser.ParseFile(fset, filepath.Join(dir, entry.Name()), nil, parser.ImportsOnly)
		if err != nil {
			continue
		}
		for _, imp := range file.Imports {
			path := strings.Trim(imp.Path.Value, `"`)
			if path != "C" {
				importSet[path] = struct{}{}
			}
		}
	}
	if !hasGo {
		return nil
	}
	rel, err := filepath.Rel(root, dir)
	if err != nil {
		return err
	}
	pkgPath := modulePath
	if rel != "." {
		pkgPath = modulePath + "/" + filepath.ToSlash(rel)
	}
	imports := make([]string, 0, len(importSet))
	for imp := range importSet {
		imports = append(imports, imp)
	}
	sort.Strings(imports)
	g.AddPackage(pkgPath, dir, imports)
	return nil
}

func modulePath(root string) (string, error) {
	data, err := os.ReadFile(filepath.Join(root, "go.mod"))
	if err != nil {
		return "", err
	}
	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "module ") {
			return strings.TrimSpace(strings.TrimPrefix(line, "module ")), nil
		}
	}
	return "", os.ErrInvalid
}
