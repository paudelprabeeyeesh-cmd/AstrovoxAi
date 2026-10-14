package sandbox

import (
	"errors"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

// This is the adversarial suite: each test is an attempt to escape or to
// exhaust the sandbox, not a verification that the happy path works.
//
// The distinction matters because a sandbox's value is entirely in the cases
// where it refuses. A test that confirms a task can allocate memory it was
// given passes whether or not the limit is enforced at all.

// --- tasks ---

// namedTask gives every task a Name, which the Task interface requires.
type namedTask struct {
	name string
	run  func(*Environment) error
}

func (t namedTask) Name() string { return t.name }
func (t namedTask) Run(env *Environment) error {
	if t.run == nil {
		return nil
	}
	return t.run(env)
}

func allowedCaps() CapabilitySet {
	// The capabilities the tasks legitimately need. Granted explicitly so a
	// refusal is about the limit rather than a missing capability.
	return CapabilitySet{
		CapMemory:    true,
		CapFileWrite: true,
		CapFileRead:  true,
		CapClock:     true,
	}
}

// escapePolicy is a sandbox with everything revoked and small limits.
func escapePolicy() Policy {
	return Policy{
		Name:         "locked",
		Capabilities: CapabilitySet{},
		Limits: ResourceLimits{
			MaxMemoryBytes: 4096,
			MaxCPUTimeMs:   100,
			MaxWallTimeMs:  200,
			MaxOpenFiles:   2,
			MaxThreads:     2,
			MaxOutputBytes: 1024,
			AllowNetwork:   false,
		},
	}
}

// permissivePolicy grants the capabilities the tasks use but keeps tight
// limits, so a refusal is unambiguously about the limit.
func permissivePolicy() Policy {
	return Policy{
		Name:         "permissive",
		Capabilities: allowedCaps(),
		Limits:       escapePolicy().Limits,
	}
}

func memoryHog(request int64) Task {
	return namedTask{name: "memory-hog", run: func(env *Environment) error {
		return env.Allocate(request)
	}}
}

func slowDrip(amount int64, times int) Task {
	return namedTask{name: "slow-drip", run: func(env *Environment) error {
		for i := 0; i < times; i++ {
			if err := env.Allocate(amount); err != nil {
				return err
			}
		}
		return nil
	}}
}

func fileHog(count int) Task {
	return namedTask{name: "file-hog", run: func(env *Environment) error {
		for i := 0; i < count; i++ {
			if err := env.OpenFile(); err != nil {
				return err
			}
		}
		return nil
	}}
}

func outputFlood(chunk []byte, times int) Task {
	return namedTask{name: "output-flood", run: func(env *Environment) error {
		for i := 0; i < times; i++ {
			if err := env.WriteOutput(chunk); err != nil {
				return err
			}
		}
		return nil
	}}
}

func cpuHog(ms int64) Task {
	return namedTask{name: "cpu-hog", run: func(env *Environment) error {
		return env.AddCPUTime(ms)
	}}
}

func capSeeker(want Capability) Task {
	return namedTask{name: "cap-seeker", run: func(env *Environment) error {
		return env.Require(want)
	}}
}

func panicking(marked *atomic.Bool) Task {
	return namedTask{name: "panicking", run: func(*Environment) error {
		marked.Store(true)
		panic("deliberate escape attempt")
	}}
}

func hanging(sleep time.Duration) Task {
	return namedTask{name: "hanging", run: func(*Environment) error {
		time.Sleep(sleep)
		return nil
	}}
}

// --- tests ---

func TestSandboxRefusesASingleOversizedAllocation(t *testing.T) {
	s := NewSandbox(permissivePolicy())
	err := s.Execute(memoryHog(1 << 30))
	if err == nil {
		t.Fatal("a sandbox with a 4KB limit allowed a 1GB allocation")
	}
	var violation *ViolationError
	if !errors.As(err, &violation) {
		t.Fatalf("the refusal was not a violation: %v", err)
	}
	if violation.Violation.Kind == "" {
		t.Fatal("the violation named no kind")
	}
}

func TestSandboxRefusesAnAllocationByDripFeed(t *testing.T) {
	// 100 in-limit allocations that together exceed the cap. A limit that only
	// checks one call at a time passes this and is defeated by any loop.
	s := NewSandbox(permissivePolicy())
	if err := s.Execute(slowDrip(400, 100)); err == nil {
		t.Fatal("a 4KB limit allowed 40KB of small allocations")
	}
}

func TestSandboxRefusesCPUOveruse(t *testing.T) {
	s := NewSandbox(permissivePolicy())
	if err := s.Execute(cpuHog(10_000)); err == nil {
		t.Fatal("a 100ms CPU limit allowed 10 seconds")
	}
}

func TestSandboxRefusesTooManyFileHandles(t *testing.T) {
	s := NewSandbox(permissivePolicy())
	if err := s.Execute(fileHog(50)); err == nil {
		t.Fatal("a 2-handle limit allowed 50 files")
	}
}

func TestSandboxRefusesOutputFloodingInSmallWrites(t *testing.T) {
	// 200 writes of 100 bytes into a 1KB cap. Checking per call passes this.
	s := NewSandbox(permissivePolicy())
	if err := s.Execute(outputFlood(make([]byte, 100), 200)); err == nil {
		t.Fatal("a 1KB output cap allowed 20KB")
	}
}

func TestSandboxRefusesAUngrantedCapability(t *testing.T) {
	s := NewSandbox(escapePolicy())
	for _, cap := range []Capability{CapNetwork, CapExec, CapEnvRead, CapFileWrite, CapMemory} {
		if err := s.Execute(capSeeker(cap)); err == nil {
			t.Fatalf("a sandbox granted nothing allowed %s", cap)
		}
	}
}

func TestSandboxCatchesAPanicInsteadOfCrashingTheProcess(t *testing.T) {
	marked := &atomic.Bool{}
	s := NewSandbox(escapePolicy())
	err := s.Execute(panicking(marked))

	if !marked.Load() {
		t.Fatal("the task did not run, so this test proved nothing about panics")
	}
	if err == nil {
		t.Fatal("a panic was swallowed without an error")
	}
	if got := s.Stats().Violations.Load() + s.Stats().TasksFailed.Load(); got == 0 {
		t.Fatal("a panicking task was recorded as neither a failure nor a violation")
	}
}

func TestSandboxEnforcesTheWallClock(t *testing.T) {
	// The watchdog must interrupt a task that never returns, not merely report
	// failure afterwards.
	s := NewSandbox(permissivePolicy())
	done := make(chan error, 1)
	start := time.Now()
	go func() { done <- s.Execute(hanging(5 * time.Second)) }()

	select {
	case err := <-done:
		elapsed := time.Since(start)
		if err == nil {
			t.Fatal("a task running past the wall limit returned success")
		}
		if elapsed > 2*time.Second {
			t.Fatalf("the watchdog reported after %v, so it did not bound the run", elapsed)
		}
	case <-time.After(3 * time.Second):
		t.Fatal("the watchdog never fired")
	}
}

func TestSandboxStatsStayConsistentUnderConcurrentViolations(t *testing.T) {
	// A fork bomb produces many concurrent abandoned units. The sandbox cannot
	// stop a task from spawning goroutines, so what it must do is record every
	// attempt without racing on its own counters.
	s := NewSandbox(escapePolicy())
	var wg sync.WaitGroup
	for i := 0; i < 64; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			_ = s.Execute(memoryHog(1 << 40))
		}()
	}
	wg.Wait()

	if got := s.Stats().TasksRun.Load(); got != 64 {
		t.Fatalf("TasksRun = %d, want 64", got)
	}
	// A violation is also a failure, so both counters move. They are asserted
	// separately rather than summed: adding them would count one event twice
	// and, worse, would let a bug that incremented only one of them pass.
	if got := s.Stats().TasksFailed.Load(); got != 64 {
		t.Fatalf("TasksFailed = %d, want 64", got)
	}
	if got := s.Stats().Violations.Load(); got != 64 {
		t.Fatalf("Violations = %d, want 64", got)
	}
}

func TestSandboxRejectsANilTask(t *testing.T) {
	if err := NewSandbox(escapePolicy()).Execute(nil); err == nil {
		t.Fatal("a nil task was accepted")
	}
}

func TestGrantsAreCopiedNotShared(t *testing.T) {
	// A task must receive a copy of the policy's capability set. Sharing it
	// means a task can grant itself a capability for the next run, which turns
	// any sandbox into one that fails once and then stops failing.
	policy := permissivePolicy()
	s := NewSandbox(policy)

	before := policy.Capabilities.Has(CapFileWrite)
	_ = s.Execute(namedTask{name: "noop"})
	after := policy.Capabilities.Has(CapFileWrite)

	if before != after || !after {
		t.Fatalf("the policy's capability set changed: before=%v after=%v", before, after)
	}
}

func TestAFailedAllocationDoesNotConsumeTheBudget(t *testing.T) {
	// A refused allocation must not leave the counter raised, or a task that
	// retries is eventually denied for memory it does not hold.
	env := &Environment{caps: allowedCaps(), limits: permissivePolicy().Limits}
	if err := env.Allocate(1 << 30); err == nil {
		t.Fatal("the oversized allocation was allowed")
	}
	if used := env.MemoryUsed(); used != 0 {
		t.Fatalf("MemoryUsed = %d after a refused allocation", used)
	}
}

func TestAFreedAllocationRestoresTheBudget(t *testing.T) {
	env := &Environment{caps: allowedCaps(), limits: permissivePolicy().Limits}
	if err := env.Allocate(1024); err != nil {
		t.Fatalf("an in-limit allocation was refused: %v", err)
	}
	env.Free(1024)
	if used := env.MemoryUsed(); used != 0 {
		t.Fatalf("MemoryUsed = %d after Free", used)
	}
	if err := env.Allocate(1024); err != nil {
		t.Fatalf("the same allocation was refused after Free: %v", err)
	}
}

func TestAClosedFileRestoresTheHandleBudget(t *testing.T) {
	env := &Environment{caps: allowedCaps(), limits: permissivePolicy().Limits}
	if err := env.OpenFile(); err != nil {
		t.Fatalf("the first handle was refused: %v", err)
	}
	if err := env.OpenFile(); err != nil {
		t.Fatalf("the second handle was refused: %v", err)
	}
	if err := env.OpenFile(); err == nil {
		t.Fatal("a third handle was allowed against a limit of two")
	}
	env.CloseFile()
	if err := env.OpenFile(); err != nil {
		t.Fatalf("a handle was not reusable after CloseFile: %v", err)
	}
}

func TestSandboxNameSanitisationRejectsEscapeAttempts(t *testing.T) {
	// A name is used to derive paths, so a traversal or a NUL is the escape.
	for _, bad := range []string{
		"", " ", "../etc/passwd", "a\x00b", "a/b", "a\\b", "..", ".",
	} {
		if _, err := SanitizeName(bad); err == nil {
			t.Fatalf("SanitizeName(%q) returned no error", bad)
		}
	}
}

func TestSandboxNameSanitisationAcceptsASafeName(t *testing.T) {
	got, err := SanitizeName("my-plugin_1.2")
	if err != nil {
		t.Fatalf("a safe name was rejected: %v", err)
	}
	if got != "my-plugin_1.2" {
		t.Fatalf("SanitizeName mangled a safe name: %q", got)
	}
}
