// Package mock provides a minimal, dependency-free
// mock framework for hermetic tests: call recording
// with ordered expectations, generic mock functions,
// and scripted return values.
package mock

import (
	"fmt"
	"reflect"
	"sync"
)

// Call records one invocation of a mocked method.
type Call struct {
	Name string
	Args []any
}

// Recorder records calls and verifies that every
// expected call happened, in order.
type Recorder struct {
	mu       sync.Mutex
	calls    []Call
	expected []Call
}

// NewRecorder returns an empty recorder.
func NewRecorder() *Recorder { return &Recorder{} }

// Record logs a call with the given arguments.
func (r *Recorder) Record(name string, args ...any) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.calls = append(r.calls, Call{Name: name, Args: args})
}

// Expect registers a call that must occur before
// Verify succeeds.
func (r *Recorder) Expect(name string, args ...any) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.expected = append(r.expected, Call{Name: name, Args: args})
}

// Calls returns all recorded calls for name.
func (r *Recorder) Calls(name string) []Call {
	r.mu.Lock()
	defer r.mu.Unlock()
	var out []Call
	for _, c := range r.calls {
		if c.Name == name {
			out = append(out, c)
		}
	}
	return out
}

// Count returns how many times name was recorded.
func (r *Recorder) Count(name string) int { return len(r.Calls(name)) }

// All returns every recorded call in order.
func (r *Recorder) All() []Call {
	r.mu.Lock()
	defer r.mu.Unlock()
	out := make([]Call, len(r.calls))
	copy(out, r.calls)
	return out
}

// Verify checks that every expected call was
// recorded, in the same relative order. Recorded
// calls without expectations are ignored.
func (r *Recorder) Verify() error {
	r.mu.Lock()
	defer r.mu.Unlock()
	i := 0
	for _, want := range r.expected {
		for ; i < len(r.calls); i++ {
			if sameCall(r.calls[i], want) {
				break
			}
		}
		if i == len(r.calls) {
			return fmt.Errorf("mock: expected call %s(%v) was not recorded", want.Name, want.Args)
		}
		i++
	}
	return nil
}

func sameCall(a, b Call) bool {
	if a.Name != b.Name || len(a.Args) != len(b.Args) {
		return false
	}
	for i := range a.Args {
		if !reflect.DeepEqual(a.Args[i], b.Args[i]) {
			return false
		}
	}
	return true
}

// Func mocks a single-argument function, recording
// every invocation.
type Func[A, R any] struct {
	mu   sync.Mutex
	impl func(A) R
	args []A
}

// NewFunc returns a mock backed by impl.
func NewFunc[A, R any](impl func(A) R) *Func[A, R] {
	return &Func[A, R]{impl: impl}
}

// SetImpl replaces the backing implementation.
func (f *Func[A, R]) SetImpl(impl func(A) R) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.impl = impl
}

// Call invokes the backing implementation and
// records the argument. It panics when no
// implementation is set.
func (f *Func[A, R]) Call(a A) R {
	f.mu.Lock()
	f.args = append(f.args, a)
	impl := f.impl
	f.mu.Unlock()
	if impl == nil {
		var zero R
		return zero
	}
	return impl(a)
}

// Args returns the recorded arguments.
func (f *Func[A, R]) Args() []A {
	f.mu.Lock()
	defer f.mu.Unlock()
	out := make([]A, len(f.args))
	copy(out, f.args)
	return out
}

// CallCount returns the number of invocations.
func (f *Func[A, R]) CallCount() int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return len(f.args)
}

// ErrorFunc mocks a single-argument function
// returning a result and an error.
type ErrorFunc[A, R any] struct {
	mu   sync.Mutex
	impl func(A) (R, error)
	args []A
}

// NewErrorFunc returns a mock backed by impl.
func NewErrorFunc[A, R any](impl func(A) (R, error)) *ErrorFunc[A, R] {
	return &ErrorFunc[A, R]{impl: impl}
}

// SetImpl replaces the backing implementation.
func (f *ErrorFunc[A, R]) SetImpl(impl func(A) (R, error)) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.impl = impl
}

// Call invokes the backing implementation and
// records the argument. It panics when no
// implementation is set.
func (f *ErrorFunc[A, R]) Call(a A) (R, error) {
	f.mu.Lock()
	f.args = append(f.args, a)
	impl := f.impl
	f.mu.Unlock()
	if impl == nil {
		var zero R
		return zero, fmt.Errorf("mock: no implementation set")
	}
	return impl(a)
}

// Args returns the recorded arguments.
func (f *ErrorFunc[A, R]) Args() []A {
	f.mu.Lock()
	defer f.mu.Unlock()
	out := make([]A, len(f.args))
	copy(out, f.args)
	return out
}

// CallCount returns the number of invocations.
func (f *ErrorFunc[A, R]) CallCount() int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return len(f.args)
}

// Stub holds one scripted result.
type Stub struct {
	Args []any // nil matches any arguments
	Rets []any
	Err  error
}

// Stubber scripts return values for named methods.
// Stubs are consumed in FIFO order per method; the
// last stub repeats once the list is exhausted.
type Stubber struct {
	mu    sync.Mutex
	stubs map[string][]Stub
}

// NewStubber returns an empty stubber.
func NewStubber() *Stubber {
	return &Stubber{stubs: make(map[string][]Stub)}
}

// Push appends a scripted result for name.
func (s *Stubber) Push(name string, stub Stub) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.stubs[name] = append(s.stubs[name], stub)
}

// Pending returns the number of unconsumed stubs
// for name.
func (s *Stubber) Pending(name string) int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return len(s.stubs[name])
}

// Next returns the scripted result for name given
// the actual call arguments. Argument matching uses
// reflect.DeepEqual; a stub with nil Args matches
// any arguments. It returns an error when no stub
// was pushed for name.
func (s *Stubber) Next(name string, args []any) ([]any, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	list := s.stubs[name]
	if len(list) == 0 {
		return nil, fmt.Errorf("mock: no stub for %s", name)
	}
	idx := 0
	for i, stub := range list {
		if stubMatches(stub.Args, args) {
			idx = i
			break
		}
	}
	stub := list[idx]
	if len(list) > 1 {
		s.stubs[name] = list[1:]
	}
	return stub.Rets, stub.Err
}

func stubMatches(want, got []any) bool {
	if want == nil {
		return true
	}
	if len(want) != len(got) {
		return false
	}
	for i := range want {
		if !reflect.DeepEqual(want[i], got[i]) {
			return false
		}
	}
	return true
}
