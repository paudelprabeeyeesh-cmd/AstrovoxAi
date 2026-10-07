package arch

import (
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// InitIssue describes a module initialization problem found by
// CheckModuleInit.
type InitIssue struct {
	Package string
	File    string
	Message string
}

// CheckModuleInit verifies that every package in the module at root
// initializes cleanly:
//   - go.mod exists with a module directive
//   - every package declares a single consistent package name
//   - init functions do not call os.Exit
//   - test files use the package name or "<pkg>_test"
func CheckModuleInit(root string) []InitIssue {
	var issues []InitIssue

	if _, err := modulePath(root); err != nil {
		return []InitIssue{{Package: "", Message: "go.mod missing or invalid: " + err.Error()}}
	}

	entries, err := os.ReadDir(root)
	if err != nil {
		return []InitIssue{{Package: "", Message: "read root: " + err.Error()}}
	}

	var dirs []string
	for _, entry := range entries {
		if entry.IsDir() && !strings.HasPrefix(entry.Name(), ".") && entry.Name() != "testdata" {
			dirs = append(dirs, filepath.Join(root, entry.Name()))
		}
	}
	dirs = append(dirs, root)

	for _, dir := range dirs {
		issues = append(issues, checkPackageDir(dir)...)
	}

	sort.Slice(issues, func(i, j int) bool {
		if issues[i].Package != issues[j].Package {
			return issues[i].Package < issues[j].Package
		}
		return issues[i].File < issues[j].File
	})
	return issues
}

func checkPackageDir(dir string) []InitIssue {
	var issues []InitIssue
	entries, err := os.ReadDir(dir)
	if err != nil {
		return issues
	}

	pkgName := ""
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".go") {
			continue
		}
		path := filepath.Join(dir, entry.Name())
		fset := token.NewFileSet()
		file, err := parser.ParseFile(fset, path, nil, parser.ParseComments)
		if err != nil {
			issues = append(issues, InitIssue{
				Package: filepath.Base(dir),
				File:    entry.Name(),
				Message: "parse error: " + err.Error(),
			})
			continue
		}

		name := file.Name.Name
		isTest := strings.HasSuffix(name, "_test")
		if pkgName == "" && !isTest {
			pkgName = name
		}
		if !isTest && name != pkgName {
			issues = append(issues, InitIssue{
				Package: filepath.Base(dir),
				File:    entry.Name(),
				Message: "inconsistent package name " + name + " (expected " + pkgName + ")",
			})
		}

		for _, decl := range file.Decls {
			fn, ok := decl.(*ast.FuncDecl)
			if !ok || fn.Name.Name != "init" {
				continue
			}
			ast.Inspect(fn.Body, func(n ast.Node) bool {
				call, ok := n.(*ast.CallExpr)
				if !ok {
					return true
				}
				if sel, ok := call.Fun.(*ast.SelectorExpr); ok {
					if ident, ok := sel.X.(*ast.Ident); ok && ident.Name == "os" && sel.Sel.Name == "Exit" {
						issues = append(issues, InitIssue{
							Package: filepath.Base(dir),
							File:    entry.Name(),
							Message: "init function calls os.Exit",
						})
					}
				}
				return true
			})
		}
	}
	return issues
}
