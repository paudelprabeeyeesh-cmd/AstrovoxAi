package compiler

import (
	"github.com/astrovox/astrovox/graph"
	"github.com/astrovox/astrovox/internal/errors"
)

// Options configures the compilation pipeline.
type Options struct {
	// Target selects the codegen backend.
	Target string // "interpreter", "llvm", "wasm"
	// Optimize enables TIR-level optimizations.
	Optimize bool
	// TileSize sets the GEMM tile dimension.
	TileSize int
}

// DefaultOptions is the standard configuration.
func DefaultOptions() Options {
	return Options{Target: "interpreter", Optimize: true, TileSize: 32}
}

// Result is the output of compilation.
type Result struct {
	Module *Module
	Target string
	Stats  Stats
}

// Stats reports compilation metrics.
type Stats struct {
	Funcs      int
	Stmts      int
	Passes     int
	Folds      int
	ElapsedNs  int64
}

// Compiler orchestrates lowering, TIR
// optimization, and code generation.
type Compiler struct {
	opts   Options
	low    *Lowerer
	tirOpt *TIROptimizer
}

// NewCompiler creates a compiler.
func NewCompiler(opts Options) (*Compiler, error) {
	if opts.TileSize <= 0 {
		opts.TileSize = 32
	}
	switch opts.Target {
	case "interpreter", "llvm", "wasm":
	default:
		return nil, errors.New(errors.CodeInvalidArgument, "unknown target").
			WithField("target", opts.Target)
	}
	return &Compiler{
		opts:   opts,
		low:    NewLowerer(),
		tirOpt: NewTIROptimizer(),
	}, nil
}

// Compile lowers the graph to the target.
// The graph compiles to a single "main"
// function: source nodes become parameters
// named "input_<nodeID>" and the sink
// node becomes the result.
func (c *Compiler) Compile(g *graph.Graph) (*Result, error) {
	fn, err := c.low.LowerSingle(g)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInternal, "lowering failed")
	}
	mod := NewModule()
	mod.Add(fn)
	passes, folds := 0, 0
	if c.opts.Optimize {
		mod, passes, folds, err = c.tirOpt.Optimize(mod)
		if err != nil {
			return nil, errors.Wrap(err, errors.CodeInternal, "TIR optimization failed")
		}
	}
	stmts := 0
	for _, name := range mod.Order {
		f := mod.Funcs[name]
		stmts += countStmts(f.Body)
	}
	return &Result{
		Module: mod,
		Target: c.opts.Target,
		Stats: Stats{
			Funcs:  len(mod.Order),
			Stmts:  stmts,
			Passes: passes,
			Folds:  folds,
		},
	}, nil
}

// countStmts recursively counts statements.
func countStmts(body []Stmt) int {
	n := 0
	for _, s := range body {
		n++
		if f, ok := s.(ForStmt); ok {
			n += countStmts(f.Body)
		}
	}
	return n
}
