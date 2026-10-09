package sandbox

import (
	"context"
	"testing"
)

type okTask struct{ name string }

func (t okTask) Name() string { return t.name }
func (t okTask) Run(env *Environment) error {
	if err := env.Require(CapMemory); err != nil {
		return err
	}
	if err := env.Allocate(1024); err != nil {
		return err
	}
	env.Free(1024)
	if err := env.AddCPUTime(1); err != nil {
		return err
	}
	return nil
}

type badTask struct{ name string }

func (t badTask) Name() string { return t.name }
func (t badTask) Run(env *Environment) error {
	return env.Allocate(1 << 40) // way over the limit
}

type panicTask struct{}

func (t panicTask) Name() string { return "panic" }
func (t panicTask) Run(env *Environment) error {
	panic("boom")
}

func TestExecuteOK(t *testing.T) {
	sb := NewSandbox(Policy{
		Capabilities: CapabilitySet{CapMemory: true, CapClock: true},
		Limits:       DefaultLimits(),
	})
	if err := sb.Execute(okTask{name: "ok"}); err != nil {
		t.Fatal(err)
	}
	st := sb.Stats()
	if st.TasksPassed.Load() != 1 {
		t.Error("expected 1 pass")
	}
}

func TestExecuteViolation(t *testing.T) {
	sb := NewSandbox(Policy{
		Capabilities: CapabilitySet{CapMemory: true},
		Limits:       DefaultLimits(),
	})
	err := sb.Execute(badTask{name: "bad"})
	if err == nil {
		t.Fatal("expected violation")
	}
	var ve *ViolationError
	if !asViolation(err, &ve) {
		t.Errorf("expected ViolationError, got %T", err)
	}
	vst := sb.Stats()
	if vst.Violations.Load() < 1 {
		t.Error("expected violation stat")
	}
}

func TestExecutePanicRecovered(t *testing.T) {
	sb := NewSandbox(Policy{Limits: DefaultLimits()})
	err := sb.Execute(panicTask{})
	if err == nil {
		t.Fatal("expected error from panic")
	}
	st := sb.Stats()
	if st.TasksFailed.Load() != 1 {
		t.Error("expected failure stat")
	}
}

func TestExecuteNilTask(t *testing.T) {
	sb := NewSandbox(Policy{Limits: DefaultLimits()})
	if sb.Execute(nil) == nil {
		t.Error("expected error for nil task")
	}
}

func TestRequireCapability(t *testing.T) {
	e := &Environment{caps: CapabilitySet{}, limits: DefaultLimits()}
	if err := e.Require(CapNetwork); err == nil {
		t.Error("expected capability denial")
	}
	e.caps[CapNetwork] = true
	if err := e.Require(CapNetwork); err != nil {
		t.Fatal(err)
	}
}

func TestEnvironmentFiles(t *testing.T) {
	e := &Environment{caps: CapabilitySet{}, limits: DefaultLimits()}
	e.limits.MaxOpenFiles = 1
	if err := e.OpenFile(); err != nil {
		t.Fatal(err)
	}
	if err := e.OpenFile(); err == nil {
		t.Error("expected file limit error")
	}
	e.CloseFile()
	if err := e.OpenFile(); err != nil {
		t.Fatal("expected success after close")
	}
}

func TestEnvironmentOutput(t *testing.T) {
	e := &Environment{
		caps:   CapabilitySet{CapFileWrite: true},
		limits: ResourceLimits{MaxOutputBytes: 4, MaxWallTimeMs: 1000},
	}
	if err := e.WriteOutput([]byte("ab")); err != nil {
		t.Fatal(err)
	}
	if err := e.WriteOutput([]byte("cdef")); err == nil {
		t.Error("expected output limit error")
	}
}

func TestEnvironmentCPUTime(t *testing.T) {
	e := &Environment{limits: ResourceLimits{MaxCPUTimeMs: 10}}
	if err := e.AddCPUTime(5); err != nil {
		t.Fatal(err)
	}
	if err := e.AddCPUTime(20); err == nil {
		t.Error("expected cpu limit error")
	}
	if e.CPUTimeMs() != 25 {
		t.Errorf("expected 25ms tracked, got %d", e.CPUTimeMs())
	}
}

func TestEnvironmentMemory(t *testing.T) {
	e := &Environment{caps: CapabilitySet{CapMemory: true}, limits: DefaultLimits()}
	if err := e.Allocate(2048); err != nil {
		t.Fatal(err)
	}
	if e.MemoryUsed() != 2048 {
		t.Errorf("expected 2048, got %d", e.MemoryUsed())
	}
	e.Free(1024)
	if e.MemoryUsed() != 1024 {
		t.Errorf("expected 1024, got %d", e.MemoryUsed())
	}
}

func TestCapabilityString(t *testing.T) {
	if CapFileRead.String() != "file.read" {
		t.Error("file.read")
	}
	if CapNetwork.String() != "network" {
		t.Error("network")
	}
	if Capability(99).String() != "unknown" {
		t.Error("unknown")
	}
}

func TestSanitizeName(t *testing.T) {
	if _, err := SanitizeName("valid-name_1.2"); err != nil {
		t.Fatal(err)
	}
	if _, err := SanitizeName("-bad"); err == nil {
		t.Error("expected error for leading dash")
	}
	if _, err := SanitizeName(""); err == nil {
		t.Error("expected error for empty")
	}
	if _, err := SanitizeName("has space"); err == nil {
		t.Error("expected error for invalid char")
	}
}

func TestCapabilitySet(t *testing.T) {
	s := CapabilitySet{}
	s.Grant(CapExec)
	if !s.Has(CapExec) {
		t.Error("expected granted")
	}
	s.Revoke(CapExec)
	if s.Has(CapExec) {
		t.Error("expected revoked")
	}
}

func TestSandboxManager(t *testing.T) {
	m := NewSandboxManager()
	if _, err := m.Create("worker", Policy{Limits: DefaultLimits()}); err != nil {
		t.Fatal(err)
	}
	if _, ok := m.Get("worker"); !ok {
		t.Error("expected sandbox")
	}
	if _, err := m.Create("bad name", Policy{}); err == nil {
		t.Error("expected sanitize error")
	}
	if _, err := m.Create("worker", Policy{}); err == nil {
		t.Error("expected duplicate error")
	}
	if len(m.List()) != 1 {
		t.Errorf("expected 1, got %d", len(m.List()))
	}
}

func TestPolicyAccessor(t *testing.T) {
	p := Policy{Name: "x", Capabilities: CapabilitySet{CapExec: true}}
	sb := NewSandbox(p)
	if sb.Policy().Name != "x" {
		t.Error("policy accessor")
	}
}

func asViolation(err error, target **ViolationError) bool {
	v, ok := err.(*ViolationError)
	if ok {
		*target = v
	}
	return ok
}

var _ = context.Background()