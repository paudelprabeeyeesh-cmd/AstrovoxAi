package mock

import (
	"errors"
	"testing"
)

func TestRecorder_RecordCount(t *testing.T) {
	r := NewRecorder()
	r.Record("foo", 1)
	r.Record("foo", 2)
	r.Record("bar")
	if c := r.Count("foo"); c != 2 {
		t.Fatalf("count = %d, want 2", c)
	}
	if c := r.Count("bar"); c != 1 {
		t.Fatalf("count = %d, want 1", c)
	}
	if c := r.Count("baz"); c != 0 {
		t.Fatalf("count = %d, want 0", c)
	}
}

func TestRecorder_All(t *testing.T) {
	r := NewRecorder()
	r.Record("a", 1)
	r.Record("b", 2)
	r.Record("a", 3)
	calls := r.All()
	if len(calls) != 3 {
		t.Fatalf("len = %d, want 3", len(calls))
	}
	if calls[0].Name != "a" || calls[0].Args[0] != 1 {
		t.Fatalf("call[0] = %v", calls[0])
	}
}

func TestRecorder_Calls_Filter(t *testing.T) {
	r := NewRecorder()
	r.Record("x", "a")
	r.Record("y", "b")
	r.Record("x", "c")
	calls := r.Calls("x")
	if len(calls) != 2 {
		t.Fatalf("len = %d, want 2", len(calls))
	}
	if calls[0].Args[0] != "a" || calls[1].Args[0] != "c" {
		t.Fatalf("calls = %v", calls)
	}
}

func TestRecorder_Verify_Success(t *testing.T) {
	r := NewRecorder()
	r.Record("init", 0)
	r.Record("work", 1)
	r.Record("work", 2)
	r.Expect("init", 0)
	r.Expect("work", 2)
	if err := r.Verify(); err != nil {
		t.Fatalf("Verify: %v", err)
	}
}

func TestRecorder_Verify_Missing(t *testing.T) {
	r := NewRecorder()
	r.Record("init", 0)
	r.Expect("init", 0)
	r.Expect("work", 1)
	if err := r.Verify(); err == nil {
		t.Fatal("expected error, got nil")
	}
}

func TestRecorder_Verify_Order(t *testing.T) {
	r := NewRecorder()
	r.Record("work", 1)
	r.Record("init", 0)
	r.Expect("init", 0)
	r.Expect("work", 1)
	if err := r.Verify(); err == nil {
		t.Fatal("expected order error, got nil")
	}
}

func TestRecorder_Verify_IgnoresExtra(t *testing.T) {
	r := NewRecorder()
	r.Record("init", 0)
	r.Record("spam")
	r.Record("work", 1)
	r.Expect("init", 0)
	r.Expect("work", 1)
	if err := r.Verify(); err != nil {
		t.Fatalf("Verify: %v", err)
	}
}

func TestFunc_Call(t *testing.T) {
	m := NewFunc(func(x int) int { return x * 2 })
	got := m.Call(3)
	if got != 6 {
		t.Fatalf("Call = %d, want 6", got)
	}
}

func TestFunc_ArgsAndCount(t *testing.T) {
	m := NewFunc(func(s string) int { return len(s) })
	_, _ = m.Call("hi"), m.Call("hello")
	if m.CallCount() != 2 {
		t.Fatalf("CallCount = %d, want 2", m.CallCount())
	}
	args := m.Args()
	if len(args) != 2 || args[0] != "hi" || args[1] != "hello" {
		t.Fatalf("Args = %v", args)
	}
}

func TestFunc_SetImpl(t *testing.T) {
	m := NewFunc(func(x int) int { return x })
	m.SetImpl(func(x int) int { return x + 1 })
	if got := m.Call(9); got != 10 {
		t.Fatalf("Call = %d, want 10", got)
	}
}

func TestFunc_NoImpl(t *testing.T) {
	var m *Func[int, int]
	defer func() {
		if r := recover(); r == nil {
			t.Fatal("expected panic from nil impl")
		}
	}()
	m.Call(1)
}

func TestErrorFunc_Call(t *testing.T) {
	m := NewErrorFunc(func(x int) (int, error) {
		if x < 0 {
			return 0, errors.New("neg")
		}
		return x * 3, nil
	})
	got, err := m.Call(4)
	if err != nil || got != 12 {
		t.Fatalf("Call(4) = (%d, %v), want (12, nil)", got, err)
	}
	_, err = m.Call(-1)
	if err == nil {
		t.Fatal("expected error for negative input")
	}
}

func TestErrorFunc_ArgsAndCount(t *testing.T) {
	m := NewErrorFunc(func(s string) (int, error) { return len(s), nil })
	m.Call("a")
	m.Call("bc")
	if m.CallCount() != 2 {
		t.Fatalf("CallCount = %d, want 2", m.CallCount())
	}
}

func TestErrorFunc_NoImpl(t *testing.T) {
	var m *ErrorFunc[int, int]
	defer func() {
		if r := recover(); r == nil {
			t.Fatal("expected panic from nil impl")
		}
	}()
	m.Call(1)
}

func TestStubber_PushNext(t *testing.T) {
	s := NewStubber()
	s.Push("f", Stub{Rets: []any{7, nil}})
	rets, err := s.Next("f", []any{1})
	if err != nil {
		t.Fatalf("Next: %v", err)
	}
	if len(rets) != 2 || rets[0] != 7 || rets[1] != nil {
		t.Fatalf("rets = %v", rets)
	}
	rets, _ = s.Next("f", []any{2})
	if len(rets) != 2 || rets[0] != 7 || rets[1] != nil {
		t.Fatalf("second pop = %v", rets)
	}
}

func TestStubber_RepeatLast(t *testing.T) {
	s := NewStubber()
	s.Push("f", Stub{Rets: []any{42}})
	s.Push("f", Stub{Rets: []any{99}})
	s.Next("f", nil)
	rets, _ := s.Next("f", nil)
	if len(rets) != 1 || rets[0] != 99 {
		t.Fatalf("second pop = %v", rets)
	}
	rets, _ = s.Next("f", nil)
	if len(rets) != 1 || rets[0] != 99 {
		t.Fatalf("repeated last = %v", rets)
	}
}

func TestStubber_NoStub(t *testing.T) {
	s := NewStubber()
	if _, err := s.Next("missing", nil); err == nil {
		t.Fatal("expected error for missing stub, got nil")
	}
}

func TestStubber_ArgMatch(t *testing.T) {
	s := NewStubber()
	s.Push("load", Stub{Args: []any{"config.yaml"}, Rets: []any{[]byte("ok"), nil}})
	s.Push("load", Stub{Rets: []any{[]byte("default"), nil}}) // any args
	rets, err := s.Next("load", []any{"config.yaml"})
	if err != nil {
		t.Fatalf("Next: %v", err)
	}
	if string(rets[0].([]byte)) != "ok" {
		t.Fatalf("rets = %v", rets)
	}
	rets, _ = s.Next("load", []any{"other.yaml"})
	if string(rets[0].([]byte)) != "default" {
		t.Fatalf("rets = %v", rets)
	}
}

func TestStubber_NilArgsMatchAny(t *testing.T) {
	s := NewStubber()
	s.Push("f", Stub{Rets: []any{99}})
	for _, args := range [][]any{nil, []any{}, []any{1, 2}} {
		rets, err := s.Next("f", args)
		if err != nil {
			t.Fatalf("Next(%v): %v", args, err)
		}
		if rets[0] != 99 {
			t.Fatalf("rets = %v", rets)
		}
	}
}

func TestStubber_Pending(t *testing.T) {
	s := NewStubber()
	if p := s.Pending("x"); p != 0 {
		t.Fatalf("pending = %d, want 0", p)
	}
	s.Push("x", Stub{Rets: []any{1}})
	s.Push("x", Stub{Rets: []any{2}})
	if p := s.Pending("x"); p != 2 {
		t.Fatalf("pending = %d, want 2", p)
	}
	s.Next("x", nil)
	if p := s.Pending("x"); p != 1 {
		t.Fatalf("pending after pop = %d, want 1", p)
	}
}

func TestRecorder_Verify_EmptyExpectations(t *testing.T) {
	r := NewRecorder()
	r.Record("anything")
	if err := r.Verify(); err != nil {
		t.Fatalf("empty expectations: %v", err)
	}
}

func TestFunc_CallCountAfterMany(t *testing.T) {
	m := NewFunc(func(x int) int { return -x })
	for i := 0; i < 50; i++ {
		m.Call(i)
	}
	if m.CallCount() != 50 {
		t.Fatalf("CallCount = %d, want 50", m.CallCount())
	}
}

func TestRecorder_Calls_EmptyName(t *testing.T) {
	r := NewRecorder()
	r.Record("", 1)
	r.Record("", 2)
	if c := r.Count(""); c != 2 {
		t.Fatalf("count = %d, want 2", c)
	}
}
