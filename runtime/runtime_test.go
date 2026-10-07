package runtime

import (
	"context"
	"sync"
	"testing"

	"github.com/astrovox/astrovox/compiler"
	"github.com/astrovox/astrovox/graph"
	"github.com/astrovox/astrovox/internal/backend"
	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
)

// linearGraph builds y = 2*x + 1 over a
// [3] source: src0 -> mul(2) -> add(1)
// with constants folded into the ops.
func linearGraph(t *testing.T) *graph.Graph {
	t.Helper()
	g := graph.New("linear")
	src, err := g.AddNode(graph.OpFunc{
		OpName:  "src",
		ShapeFn: func([]tensor.Shape) ([]tensor.Shape, error) {
			return []tensor.Shape{tensor.MustShape(3)}, nil
		},
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	mul, err := g.AddNode(graph.OpFunc{
		OpName: "mul",
		ShapeFn: func(in []tensor.Shape) ([]tensor.Shape, error) {
			return []tensor.Shape{in[0]}, nil
		},
		ForwardFn: func(in []*tensor.Tensor) ([]*tensor.Tensor, error) {
			return scaleBy(in[0], 2)
		},
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	add, err := g.AddNode(graph.OpFunc{
		OpName: "add",
		ShapeFn: func(in []tensor.Shape) ([]tensor.Shape, error) {
			return []tensor.Shape{in[0]}, nil
		},
		ForwardFn: func(in []*tensor.Tensor) ([]*tensor.Tensor, error) {
			return offsetBy(in[0], 1)
		},
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := g.AddEdge(src, mul, 0, 0); err != nil {
		t.Fatal(err)
	}
	if _, err := g.AddEdge(mul, add, 0, 0); err != nil {
		t.Fatal(err)
	}
	if err := g.MarkOutput(add); err != nil {
		t.Fatal(err)
	}
	return g
}

func scaleBy(in *tensor.Tensor, s float64) ([]*tensor.Tensor, error) {
	src := in.Float64()
	out, err := tensor.New(in.DType(), in.Shape().Dims())
	if err != nil {
		return nil, err
	}
	dst := out.Float64()
	for i, v := range src {
		dst[i] = v * s
	}
	return []*tensor.Tensor{out}, nil
}

func offsetBy(in *tensor.Tensor, o float64) ([]*tensor.Tensor, error) {
	src := in.Float64()
	out, err := tensor.New(in.DType(), in.Shape().Dims())
	if err != nil {
		return nil, err
	}
	dst := out.Float64()
	for i, v := range src {
		dst[i] = v + o
	}
	return []*tensor.Tensor{out}, nil
}

func TestSessionRun(t *testing.T) {
	g := linearGraph(t)
	sess, err := NewSession(g)
	if err != nil {
		t.Fatal(err)
	}
	x, err := tensor.New(tensor.Float64, []int{3})
	if err != nil {
		t.Fatal(err)
	}
	for i, v := range []float64{1, 2, 3} {
		if err := x.Set(v, i); err != nil {
			t.Fatal(err)
		}
	}
	out, err := sess.Run(t.Context(), []*tensor.Tensor{x})
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != 1 {
		t.Fatalf("outputs = %d, want 1", len(out))
	}
	got := out[0].Float64()
	want := []float64{3, 5, 7}
	for i, v := range got {
		if v != want[i] {
			t.Fatalf("out[%d] = %v, want %v", i, v, want[i])
		}
	}
}

// twoSourceAddGraph builds y = x0 + x1
// over [3], the minimal binary graph the
// TIR lowerer supports.
func twoSourceAddGraph(t *testing.T) *graph.Graph {
	t.Helper()
	g := graph.New("add2")
	mk := func(name string) int {
		id, err := g.AddNode(graph.OpFunc{
			OpName:  name,
			ShapeFn: func([]tensor.Shape) ([]tensor.Shape, error) {
				return []tensor.Shape{tensor.MustShape(3)}, nil
			},
		}, nil)
		if err != nil {
			t.Fatal(err)
		}
		return id
	}
	n0 := mk("src0")
	n1 := mk("src1")
	n2, err := g.AddNode(graph.OpFunc{
		OpName: "add",
		ShapeFn: func(in []tensor.Shape) ([]tensor.Shape, error) {
			return []tensor.Shape{in[0]}, nil
		},
		ForwardFn: func(in []*tensor.Tensor) ([]*tensor.Tensor, error) {
			a := in[0].Float64()
			b := in[1].Float64()
			out, err := tensor.New(in[0].DType(), in[0].Shape().Dims())
			if err != nil {
				return nil, err
			}
			dst := out.Float64()
			for i := range a {
				dst[i] = a[i] + b[i]
			}
			return []*tensor.Tensor{out}, nil
		},
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := g.AddEdge(n0, n2, 0, 0); err != nil {
		t.Fatal(err)
	}
	if _, err := g.AddEdge(n1, n2, 0, 1); err != nil {
		t.Fatal(err)
	}
	if err := g.MarkOutput(n2); err != nil {
		t.Fatal(err)
	}
	return g
}

func TestSessionCompileAndRunCompiled(t *testing.T) {
	g := twoSourceAddGraph(t)
	sess, err := NewSession(g, WithDevice(backend.DeviceCPU))
	if err != nil {
		t.Fatal(err)
	}
	if sess.IsCompiled() {
		t.Fatal("session should not start compiled")
	}
	if err := sess.Compile(compiler.DefaultOptions()); err != nil {
		t.Fatal(err)
	}
	if !sess.IsCompiled() {
		t.Fatal("session should be compiled")
	}
	names, err := sess.InputNames()
	if err != nil {
		t.Fatal(err)
	}
	if len(names) != 2 {
		t.Fatalf("input names = %v, want 2", names)
	}
	// Discover the output buffer name
	// from the compiled module.
	f, ok := sess.Module().Get("main")
	if !ok {
		t.Fatal("main function missing")
	}
	outName := f.Output.Name
	// y = x0 + x1 = [1+10, 2+20, 3+30] = [11, 22, 33]
	params := map[string][]float64{
		names[0]: {1, 2, 3},
		names[1]: {10, 20, 30},
	}
	out, err := sess.RunCompiled("main", params)
	if err != nil {
		t.Fatal(err)
	}
	got := out[outName]
	if got == nil {
		t.Fatalf("output keys = %v, want %q", keysOf(out), outName)
	}
	want := []float64{11, 22, 33}
	for i, v := range got {
		if v != want[i] {
			t.Fatalf("out[%d] = %v, want %v", i, v, want[i])
		}
	}
}

func keysOf(m map[string][]float64) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	return out
}

func TestSessionNotCompiled(t *testing.T) {
	g := linearGraph(t)
	sess, err := NewSession(g)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := sess.RunCompiled("main", nil); err == nil {
		t.Fatal("expected not-compiled error")
	}
	if _, err := sess.InputNames(); err == nil {
		t.Fatal("expected not-compiled error")
	}
}

func TestSessionInvalidGraph(t *testing.T) {
	if _, err := NewSession(nil); err == nil {
		t.Fatal("expected nil graph error")
	}
}

func TestSessionInferOutputs(t *testing.T) {
	g := linearGraph(t)
	sess, err := NewSession(g)
	if err != nil {
		t.Fatal(err)
	}
	shapes, err := sess.InferOutputs()
	if err != nil {
		t.Fatal(err)
	}
	if len(shapes) != 1 || shapes[0].Rank() != 1 || shapes[0].Dim(0) != 3 {
		t.Fatalf("shapes = %v", shapes)
	}
}

func TestSessionClose(t *testing.T) {
	g := twoSourceAddGraph(t)
	sess, err := NewSession(g)
	if err != nil {
		t.Fatal(err)
	}
	if err := sess.Compile(compiler.DefaultOptions()); err != nil {
		t.Fatal(err)
	}
	if err := sess.Close(); err != nil {
		t.Fatal(err)
	}
	if sess.IsCompiled() {
		t.Fatal("session should be uncompiled after Close")
	}
}

func TestEngineSubmit(t *testing.T) {
	engine := NewEngine(2)
	defer engine.Stop()
	var mu sync.Mutex
	var results []int
	futures := make([]Future, 0, 10)
	for i := 0; i < 10; i++ {
		i := i
		f := engine.Submit(t.Context(), func(context.Context) ([]*tensor.Tensor, error) {
			mu.Lock()
			results = append(results, i)
			mu.Unlock()
			return nil, nil
		})
		futures = append(futures, f)
	}
	if err := engine.Wait(futures...); err != nil {
		t.Fatal(err)
	}
	if len(results) != 10 {
		t.Fatalf("results = %d, want 10", len(results))
	}
	submitted, active, completed, failed := engine.Stats()
	if submitted != 10 || completed != 10 || failed != 0 {
		t.Fatalf("stats = %d %d %d %d", submitted, active, completed, failed)
	}
	if active != 0 {
		t.Fatalf("active = %d, want 0", active)
	}
}

func TestEngineSubmitError(t *testing.T) {
	engine := NewEngine(1)
	defer engine.Stop()
	sentinel := errors.New(errors.CodeInternal, "boom")
	f := engine.Submit(t.Context(), func(context.Context) ([]*tensor.Tensor, error) {
		return nil, sentinel
	})
	if _, err := f.Wait(); err == nil {
		t.Fatal("expected error")
	}
	_, _, _, failed := engine.Stats()
	if failed != 1 {
		t.Fatalf("failed = %d, want 1", failed)
	}
}

func TestEngineSubmitMany(t *testing.T) {
	engine := NewEngine(2)
	defer engine.Stop()
	tasks := make([]Task, 0, 5)
	for i := 0; i < 5; i++ {
		tasks = append(tasks, func(context.Context) ([]*tensor.Tensor, error) {
			return nil, nil
		})
	}
	futures := engine.SubmitMany(t.Context(), tasks)
	if len(futures) != 5 {
		t.Fatalf("futures = %d, want 5", len(futures))
	}
	if err := engine.Wait(futures...); err != nil {
		t.Fatal(err)
	}
}

func TestEngineForeignFuture(t *testing.T) {
	engine := NewEngine(1)
	defer engine.Stop()
	// A foreign Future implementation must
	// be rejected.
	err := engine.Wait(foreignFuture{})
	if err == nil {
		t.Fatal("expected foreign future error")
	}
	// A typed future that was never
	// submitted must also be rejected.
	err = engine.Wait(&typedFuture{})
	if err == nil {
		t.Fatal("expected unsubmitted future error")
	}
}

// foreignFuture is a Future implementation
// from outside the engine, used to verify
// type rejection.
type foreignFuture struct{}

func (foreignFuture) Wait() ([]*tensor.Tensor, error) {
	return nil, nil
}

func (foreignFuture) Done() bool { return true }

func TestFutureDone(t *testing.T) {
	engine := NewEngine(1)
	defer engine.Stop()
	f := engine.Submit(t.Context(), func(context.Context) ([]*tensor.Tensor, error) {
		return nil, nil
	})
	if _, err := f.Wait(); err != nil {
		t.Fatal(err)
	}
	if !f.Done() {
		t.Fatal("future should be done")
	}
}

func TestMemoryManagerAllocate(t *testing.T) {
	mm := NewMemoryManager(1024)
	buf, err := mm.Allocate(10)
	if err != nil {
		t.Fatal(err)
	}
	if len(buf) != 10 {
		t.Fatalf("len = %d, want 10", len(buf))
	}
	stats := mm.Stats()
	if stats.AllocatedBytes != 80 {
		t.Fatalf("allocated = %d, want 80", stats.AllocatedBytes)
	}
	if stats.LiveBuffers != 1 {
		t.Fatalf("live = %d, want 1", stats.LiveBuffers)
	}
	if stats.PeakBytes != 80 {
		t.Fatalf("peak = %d, want 80", stats.PeakBytes)
	}
	mm.Free(buf)
	stats = mm.Stats()
	if stats.AllocatedBytes != 0 {
		t.Fatalf("allocated after free = %d, want 0", stats.AllocatedBytes)
	}
	if stats.TotalAllocs != 1 || stats.TotalFrees != 1 {
		t.Fatalf("allocs/frees = %d/%d", stats.TotalAllocs, stats.TotalFrees)
	}
}

func TestMemoryManagerLimit(t *testing.T) {
	mm := NewMemoryManager(64)
	if _, err := mm.Allocate(9); err == nil {
		t.Fatal("expected limit error")
	}
	buf, err := mm.Allocate(8)
	if err != nil {
		t.Fatal(err)
	}
	mm.Free(buf)
}

func TestMemoryManagerNegative(t *testing.T) {
	mm := NewMemoryManager(0)
	if _, err := mm.Allocate(-1); err == nil {
		t.Fatal("expected negative error")
	}
}

func TestMemoryManagerUnlimited(t *testing.T) {
	mm := NewMemoryManager(0)
	buf, err := mm.Allocate(1000)
	if err != nil {
		t.Fatal(err)
	}
	stats := mm.Stats()
	if stats.LimitBytes != 0 {
		t.Fatalf("limit = %d, want 0", stats.LimitBytes)
	}
	if stats.FreeBytes != 0 {
		t.Fatalf("free = %d, want 0 for unlimited", stats.FreeBytes)
	}
	mm.Free(buf)
}

func TestMemoryManagerSetLimit(t *testing.T) {
	mm := NewMemoryManager(0)
	mm.SetLimit(16)
	if _, err := mm.Allocate(3); err == nil {
		t.Fatal("expected limit error")
	}
}

func TestArena(t *testing.T) {
	mm := NewMemoryManager(0)
	arena, err := NewArena(mm, 10)
	if err != nil {
		t.Fatal(err)
	}
	a, err := arena.Allocate(4)
	if err != nil {
		t.Fatal(err)
	}
	if len(a) != 4 {
		t.Fatalf("len = %d, want 4", len(a))
	}
	if arena.Remaining() != 6 {
		t.Fatalf("remaining = %d, want 6", arena.Remaining())
	}
	b, err := arena.Allocate(4)
	if err != nil {
		t.Fatal(err)
	}
	if len(b) != 4 {
		t.Fatalf("len = %d, want 4", len(b))
	}
	// Only 2 elements left.
	if _, err := arena.Allocate(3); err == nil {
		t.Fatal("expected exhaustion error")
	}
	arena.Reset()
	if arena.Remaining() != 10 {
		t.Fatalf("remaining after reset = %d, want 10", arena.Remaining())
	}
	arena.Release()
	stats := mm.Stats()
	if stats.LiveBuffers != 0 {
		t.Fatalf("live = %d, want 0 after release", stats.LiveBuffers)
	}
}

func TestArenaNegative(t *testing.T) {
	mm := NewMemoryManager(0)
	arena, err := NewArena(mm, 4)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := arena.Allocate(-1); err == nil {
		t.Fatal("expected negative error")
	}
}

func TestStreamEnqueue(t *testing.T) {
	engine := NewEngine(1)
	defer engine.Stop()
	stream := NewStream(engine)
	var mu sync.Mutex
	order := make([]int, 0, 3)
	for i := 0; i < 3; i++ {
		i := i
		_, err := stream.Enqueue(func(context.Context) ([]*tensor.Tensor, error) {
			mu.Lock()
			order = append(order, i)
			mu.Unlock()
			return nil, nil
		})
		if err != nil {
			t.Fatal(err)
		}
	}
	if err := stream.Synchronize(); err != nil {
		t.Fatal(err)
	}
	if len(order) != 3 {
		t.Fatalf("order = %v, want 3 entries", order)
	}
	if stream.Pending() != 3 {
		t.Fatalf("pending = %d, want 3", stream.Pending())
	}
}

func TestStreamClose(t *testing.T) {
	engine := NewEngine(1)
	defer engine.Stop()
	stream := NewStream(engine)
	_, err := stream.Enqueue(func(context.Context) ([]*tensor.Tensor, error) {
		return nil, nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if err := stream.Close(); err != nil {
		t.Fatal(err)
	}
	if _, err := stream.Enqueue(func(context.Context) ([]*tensor.Tensor, error) {
		return nil, nil
	}); err == nil {
		t.Fatal("expected closed error")
	}
}

func TestStreamNilTask(t *testing.T) {
	engine := NewEngine(1)
	defer engine.Stop()
	stream := NewStream(engine)
	if _, err := stream.Enqueue(nil); err == nil {
		t.Fatal("expected nil task error")
	}
}

func TestStreamPropagatesError(t *testing.T) {
	engine := NewEngine(1)
	defer engine.Stop()
	stream := NewStream(engine)
	_, err := stream.Enqueue(func(context.Context) ([]*tensor.Tensor, error) {
		return nil, errors.New(errors.CodeInternal, "fail")
	})
	if err != nil {
		t.Fatal(err)
	}
	if err := stream.Synchronize(); err == nil {
		t.Fatal("expected propagated error")
	}
}

func TestGraphExecutorIntegration(t *testing.T) {
	// Verify the graph package executor via
	// the session: two sources, one add.
	g := graph.New("two")
	n0, _ := g.AddNode(graph.OpFunc{
		OpName:  "a",
		ShapeFn: func([]tensor.Shape) ([]tensor.Shape, error) {
			return []tensor.Shape{tensor.MustShape(2)}, nil
		},
	}, nil)
	n1, _ := g.AddNode(graph.OpFunc{
		OpName:  "b",
		ShapeFn: func([]tensor.Shape) ([]tensor.Shape, error) {
			return []tensor.Shape{tensor.MustShape(2)}, nil
		},
	}, nil)
	n2, _ := g.AddNode(graph.OpFunc{
		OpName: "sum",
		ShapeFn: func(in []tensor.Shape) ([]tensor.Shape, error) {
			return []tensor.Shape{in[0]}, nil
		},
		ForwardFn: func(in []*tensor.Tensor) ([]*tensor.Tensor, error) {
			a := in[0].Float64()
			b := in[1].Float64()
			out, err := tensor.New(in[0].DType(), in[0].Shape().Dims())
			if err != nil {
				return nil, err
			}
			dst := out.Float64()
			for i := range a {
				dst[i] = a[i] + b[i]
			}
			return []*tensor.Tensor{out}, nil
		},
	}, nil)
	if _, err := g.AddEdge(n0, n2, 0, 0); err != nil {
		t.Fatal(err)
	}
	if _, err := g.AddEdge(n1, n2, 0, 1); err != nil {
		t.Fatal(err)
	}
	if err := g.MarkOutput(n2); err != nil {
		t.Fatal(err)
	}
	sess, err := NewSession(g)
	if err != nil {
		t.Fatal(err)
	}
	a, _ := tensor.New(tensor.Float64, []int{2})
	_ = a.Set(1, 0)
	_ = a.Set(2, 1)
	b, _ := tensor.New(tensor.Float64, []int{2})
	_ = b.Set(10, 0)
	_ = b.Set(20, 1)
	out, err := sess.Run(t.Context(), []*tensor.Tensor{a, b})
	if err != nil {
		t.Fatal(err)
	}
	got := out[0].Float64()
	if got[0] != 11 || got[1] != 22 {
		t.Fatalf("result = %v, want [11 22]", got)
	}
}

func TestInternalErrorsPackage(t *testing.T) {
	// Verify the internal errors package
	// contract used across the runtime.
	err := errors.New(errors.CodeUnimplemented, "test")
	if errors.CodeOf(err) != errors.CodeUnimplemented {
		t.Fatal("internal errors package not in use")
	}
	wrapped := errors.Wrap(err, errors.CodeInternal, "wrap")
	if errors.CodeOf(wrapped) != errors.CodeInternal {
		t.Fatalf("wrapped code = %v", errors.CodeOf(wrapped))
	}
}