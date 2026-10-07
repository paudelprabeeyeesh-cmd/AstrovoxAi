// Package runtime implements the Astrovox
// execution runtime: sessions binding compiled
// graphs to devices, an async execution engine
// over the internal scheduler, runtime memory
// management, and ordered execution streams.
package runtime

import (
	"context"
	"sync"

	"github.com/astrovox/astrovox/compiler"
	"github.com/astrovox/astrovox/graph"
	"github.com/astrovox/astrovox/internal/backend"
	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
)

// Session binds a computational graph to an
// execution target. A session executes either
// the graph directly through the graph executor
// or, after Compile, through the compiled TIR
// module on the interpreter backend.
type Session struct {
	mu       sync.RWMutex
	g        *graph.Graph
	exec     *graph.Executor
	device   backend.Device
	compiled bool
	mod      *compiler.Module
	interp   *compiler.Interpreter
	// Profiler records node execution spans.
	profiler graph.SpanRecorder
}

// SessionOption configures a session.
type SessionOption func(*Session) error

// WithDevice selects the execution device.
func WithDevice(dev backend.Device) SessionOption {
	return func(s *Session) error {
		s.device = dev
		return nil
	}
}

// WithProfiler installs a span recorder.
func WithProfiler(p graph.SpanRecorder) SessionOption {
	return func(s *Session) error {
		s.profiler = p
		return nil
	}
}

// NewSession creates a session for the graph.
func NewSession(g *graph.Graph, opts ...SessionOption) (*Session, error) {
	if g == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil graph")
	}
	exec, err := graph.NewExecutor(g)
	if err != nil {
		return nil, errors.Wrap(err, errors.CodeInvalidArgument, "invalid graph")
	}
	s := &Session{g: g, exec: exec, device: backend.DeviceCPU}
	for _, opt := range opts {
		if err := opt(s); err != nil {
			return nil, err
		}
	}
	if s.profiler != nil {
		s.exec.SetProfiler(s.profiler)
	}
	return s, nil
}

// Graph returns the bound graph.
func (s *Session) Graph() *graph.Graph { return s.g }

// Device returns the execution device.
func (s *Session) Device() backend.Device { return s.device }

// IsCompiled reports whether the session has
// a compiled module.
func (s *Session) IsCompiled() bool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.compiled
}

// Module returns the compiled module, if any.
func (s *Session) Module() *compiler.Module {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.mod
}

// Compile lowers the graph to TIR and prepares
// the interpreter backend. After Compile, Run
// dispatches through the compiled module.
func (s *Session) Compile(opts compiler.Options) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	c, err := compiler.NewCompiler(opts)
	if err != nil {
		return errors.Wrap(err, errors.CodeInvalidArgument, "compiler options")
	}
	res, err := c.Compile(s.g)
	if err != nil {
		return errors.Wrap(err, errors.CodeInternal, "compilation failed")
	}
	s.mod = res.Module
	s.interp = compiler.NewInterpreter()
	s.compiled = true
	return nil
}

// InputNames returns the compiled main
// function's parameter names, in order.
func (s *Session) InputNames() ([]string, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if !s.compiled || s.mod == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "session not compiled")
	}
	f, ok := s.mod.Get("main")
	if !ok {
		return nil, errors.New(errors.CodeInternal, "main function missing")
	}
	names := make([]string, 0, len(f.Params))
	for _, p := range f.Params {
		names = append(names, p.Name)
	}
	return names, nil
}

// Run executes the session with the given
// source-node inputs, returning sink-node
// outputs in node-ID order.
func (s *Session) Run(ctx context.Context, inputs []*tensor.Tensor) ([]*tensor.Tensor, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.exec.Run(ctx, inputs)
}

// RunCompiled executes the named compiled
// function over flat parameter buffers.
func (s *Session) RunCompiled(fnName string, params map[string][]float64) (map[string][]float64, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if !s.compiled || s.interp == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "session not compiled")
	}
	return s.interp.Execute(s.mod, fnName, params)
}

// InferOutputs returns the statically inferred
// sink shapes.
func (s *Session) InferOutputs() ([]tensor.Shape, error) {
	return s.exec.InferOutputs()
}

// Close releases session resources.
func (s *Session) Close() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.mod = nil
	s.interp = nil
	s.compiled = false
	return nil
}
