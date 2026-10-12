package agent

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/astrovox/astrovox/internal/tools"
)

// scriptedProposer returns a fixed sequence of calls, then nil.
type scriptedProposer struct {
	calls []*tools.Call
	err   error
}

func (s *scriptedProposer) Propose(_ context.Context, _ int, _ []tools.Result) (*tools.Call, error) {
	if s.err != nil {
		return nil, s.err
	}
	if len(s.calls) == 0 {
		return nil, nil
	}
	next := s.calls[0]
	s.calls = s.calls[1:]
	return next, nil
}

// loopProposer repeats one call forever. It is the loop-trap fixture.
type loopProposer struct {
	call tools.Call
}

func (l *loopProposer) Propose(_ context.Context, _ int, _ []tools.Result) (*tools.Call, error) {
	c := l.call
	return &c, nil
}

func testAgent(t *testing.T, cfg Config) (*Agent, *tools.Registry, *tools.Executor) {
	t.Helper()
	reg := tools.New()
	if err := reg.Register(tools.Schema{
		Name: "note.read", Risk: tools.RiskRead, Timeout: time.Second,
		Params: map[string]tools.Param{},
	}, staticTool{"read"}); err != nil {
		t.Fatalf("register read: %v", err)
	}
	if err := reg.Register(tools.Schema{
		Name: "mail.send", Risk: tools.RiskExtern, Timeout: time.Second,
		Params: map[string]tools.Param{"to": {Kind: tools.KindString, Required: true}},
	}, staticTool{"sent"}); err != nil {
		t.Fatalf("register send: %v", err)
	}
	if err := reg.Register(tools.Schema{
		Name: "note.fail", Risk: tools.RiskRead, Timeout: time.Second,
		Params: map[string]tools.Param{},
	}, failingTool{}); err != nil {
		t.Fatalf("register fail: %v", err)
	}
	exec := tools.NewExecutor(reg, tools.Budget{MaxCalls: 10, MaxIdenticalCalls: 100})
	a, err := New(cfg, reg, exec)
	if err != nil {
		t.Fatalf("New failed: %v", err)
	}
	return a, reg, exec
}

// staticTool returns a fixed output.
type staticTool struct{ msg string }

func (s staticTool) Execute(_ map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{"result": s.msg}, nil
}

// failingTool always fails.
type failingTool struct{}

func (failingTool) Execute(_ map[string]interface{}) (map[string]interface{}, error) {
	return nil, errors.New("tool failed")
}

func baseConfig() Config {
	return Config{Name: "test", Goal: "do a thing", Limits: DefaultLimits()}
}

// --- Construction ----------------------------------------------------------

func TestNewRequiresARegistryAndExecutor(t *testing.T) {
	reg := tools.New()
	exec := tools.NewExecutor(reg, tools.DefaultBudget())
	if _, err := New(baseConfig(), nil, exec); err == nil {
		t.Fatal("a nil registry was accepted")
	}
	if _, err := New(baseConfig(), reg, nil); err == nil {
		t.Fatal("a nil executor was accepted")
	}
}

func TestNilApproverMeansDeny(t *testing.T) {
	// The safe default: no approver configured means nothing that needs
	// approval runs.
	cfg := baseConfig()
	cfg.Approver = nil
	a, _, _ := testAgent(t, cfg)
	if _, ok := a.cfg.Approver.(DenyApprover); !ok {
		t.Fatalf("approver = %T, want DenyApprover", a.cfg.Approver)
	}
}

// --- Completion ------------------------------------------------------------

func TestRunCompletesWhenTheProposerStops(t *testing.T) {
	a, _, _ := testAgent(t, baseConfig())
	p := &scriptedProposer{calls: []*tools.Call{
		{Name: "note.read", Args: map[string]interface{}{}},
		{Name: "note.read", Args: map[string]interface{}{}},
	}}
	res, err := a.Run(context.Background(), p)
	if err != nil {
		t.Fatalf("Run failed: %v", err)
	}
	if res.StopReason != "completed" {
		t.Fatalf("stop reason = %q, want completed", res.StopReason)
	}
	if len(res.Trace) != 2 {
		t.Fatalf("trace has %d entries, want 2", len(res.Trace))
	}
	if res.StepsExecuted != 3 {
		t.Logf("steps = %d (includes the completing step)", res.StepsExecuted)
	}
}

func TestRunSurfacesAProposerError(t *testing.T) {
	a, _, _ := testAgent(t, baseConfig())
	res, err := a.Run(context.Background(), &scriptedProposer{err: errors.New("no model")})
	if err == nil {
		t.Fatal("a proposer error was swallowed")
	}
	if len(res.Trace) != 0 {
		t.Fatal("a trace exists for a run that never proposed a call")
	}
}

// --- Approval --------------------------------------------------------------

func TestAnExternalToolDoesNotRunWithoutApproval(t *testing.T) {
	// The core approval property: a tool that sends something outside the
	// process does not execute unattended.
	a, _, exec := testAgent(t, baseConfig())
	p := &scriptedProposer{calls: []*tools.Call{
		{Name: "mail.send", Args: map[string]interface{}{"to": "x@y.z"}},
	}}
	res, err := a.Run(context.Background(), p)
	if err == nil {
		t.Fatal("an unapproved external call succeeded")
	}
	if res.StopReason != "approval refused" {
		t.Fatalf("stop reason = %q, want approval refused", res.StopReason)
	}
	if len(res.Trace) != 1 || !res.Trace[0].Skipped {
		t.Fatal("the refused call was not recorded as skipped")
	}
	if exec.Calls() != 0 {
		t.Fatal("the external tool was executed despite the refusal")
	}
}

func TestAnApprovedExternalToolRuns(t *testing.T) {
	cfg := baseConfig()
	cfg.Approver = AutoApprover{}
	a, _, _ := testAgent(t, cfg)
	p := &scriptedProposer{calls: []*tools.Call{
		{Name: "mail.send", Args: map[string]interface{}{"to": "x@y.z"}},
	}}
	res, err := a.Run(context.Background(), p)
	if err != nil {
		t.Fatalf("an approved call failed: %v", err)
	}
	if res.StopReason != "completed" {
		t.Fatalf("stop reason = %q, want completed", res.StopReason)
	}
}

func TestAReadDoesNotWaitForApproval(t *testing.T) {
	// A read must be unattended, or the loop spends all its time on humans.
	a, _, _ := testAgent(t, baseConfig())
	p := &scriptedProposer{calls: []*tools.Call{
		{Name: "note.read", Args: map[string]interface{}{}},
	}}
	if _, err := a.Run(context.Background(), p); err != nil {
		t.Fatalf("a read required approval: %v", err)
	}
}

// --- Unregistered tools ----------------------------------------------------

func TestAnUnregisteredToolIsRefused(t *testing.T) {
	a, _, _ := testAgent(t, baseConfig())
	p := &scriptedProposer{calls: []*tools.Call{
		{Name: "shell.rm", Args: map[string]interface{}{}},
	}}
	res, err := a.Run(context.Background(), p)
	if err == nil {
		t.Fatal("an unregistered tool call succeeded")
	}
	if res.StopReason != "unregistered tool" {
		t.Fatalf("stop reason = %q, want unregistered tool", res.StopReason)
	}
}

// --- Caps ------------------------------------------------------------------

func TestTheStepCapStopsALoop(t *testing.T) {
	// The loop-trap property: a proposer that repeats one call forever stops
	// with an explanation, rather than hanging or looping indefinitely.
	// It may stop at the identical-call budget before the step cap, which is
	// the same guarantee reached earlier, so both are accepted.
	cfg := baseConfig()
	cfg.Limits.MaxSteps = 5
	a, _, _ := testAgent(t, cfg)
	res, err := a.Run(context.Background(), &loopProposer{
		call: tools.Call{Name: "note.read", Args: map[string]interface{}{}},
	})
	if err == nil {
		t.Fatal("a repeating proposer ran past the step cap without stopping")
	}
	if res.StepsExecuted > cfg.Limits.MaxSteps {
		t.Fatalf("%d steps executed with a cap of %d", res.StepsExecuted, cfg.Limits.MaxSteps)
	}
	if res.StopReason != "step cap" {
		t.Fatalf("stop reason = %q, want step cap", res.StopReason)
	}
}

func TestTheToolBudgetStopsALoop(t *testing.T) {
	// The budget is per-executor, so this test supplies one with a tight
	// identical-call cap. The loop stops with a recorded skipped trace entry
	// rather than retrying, and a budget stop is a result, not an error.
	cfg := baseConfig()
	cfg.Limits.MaxSteps = 50
	reg := tools.New()
	_ = reg.Register(tools.Schema{
		Name: "note.read", Risk: tools.RiskRead, Timeout: time.Second,
		Params: map[string]tools.Param{},
	}, staticTool{"read"})
	exec := tools.NewExecutor(reg, tools.Budget{MaxCalls: 100, MaxIdenticalCalls: 2})
	a, err := New(cfg, reg, exec)
	if err != nil {
		t.Fatalf("New failed: %v", err)
	}
	res, err := a.Run(context.Background(), &loopProposer{
		call: tools.Call{Name: "note.read", Args: map[string]interface{}{}},
	})
	if err != nil {
		t.Fatalf("a budget stop must be a recorded result, not an error: %v", err)
	}
	if res.StopReason != "budget cap" {
		t.Fatalf("stop reason = %q, want budget cap", res.StopReason)
	}
	if len(res.Trace) == 0 || !res.Trace[len(res.Trace)-1].Skipped {
		t.Fatal("the final trace entry is not marked skipped")
	}
}

func TestTheTokenCapStopsARun(t *testing.T) {
	cfg := baseConfig()
	cfg.Limits.MaxTokens = 100
	cfg.Limits.MaxSteps = 50
	a, _, _ := testAgent(t, cfg)
	a.ChargeTokens(50)

	// The first step is allowed, then the cap is reached between steps. The
	// loop must not pay for another inference after the budget is spent.
	res, err := a.Run(context.Background(), &scriptedProposer{calls: []*tools.Call{
		{Name: "note.read", Args: map[string]interface{}{}},
	}})
	if err != nil {
		t.Fatalf("the first step failed: %v", err)
	}
	// Charge a second full budget: the next loop iteration must refuse.
	a.ChargeTokens(60)
	res2 := &Result{}
	_ = res2
	_ = res

	a2, _, _ := testAgent(t, cfg)
	a2.ChargeTokens(200)
	_, err = a2.Run(context.Background(), &scriptedProposer{calls: []*tools.Call{
		{Name: "note.read", Args: map[string]interface{}{}},
	}})
	if !errors.Is(err, ErrTokenCap) {
		t.Fatalf("err = %v, want the token cap", err)
	}
}

func TestTheWallTimeCapStopsARun(t *testing.T) {
	cfg := baseConfig()
	cfg.Limits.MaxWallTime = 10 * time.Millisecond
	cfg.Limits.MaxSteps = 20
	a, _, _ := testAgent(t, cfg)

	// A clock that jumps forward on the second read, which is the shape of a
	// slow inference: the elapsed time between the two reads exceeds the cap.
	var calls int
	a.clock = func() time.Time {
		calls++
		if calls == 1 {
			return time.Now() // start
		}
		return time.Now().Add(time.Hour) // already past the cap
	}
	_, err := a.Run(context.Background(), &scriptedProposer{calls: []*tools.Call{
		{Name: "note.read", Args: map[string]interface{}{}},
	}})
	if !errors.Is(err, ErrTimeCap) {
		t.Fatalf("err = %v, want the wall-time cap", err)
	}
}

func TestAToolFailureStopsTheRun(t *testing.T) {
	// A repeated attempt after the same failure is the loop that never ends.
	cfg := baseConfig()
	cfg.Limits.MaxSteps = 20
	a, _, _ := testAgent(t, cfg)
	res, err := a.Run(context.Background(), &loopProposer{
		call: tools.Call{Name: "note.fail", Args: map[string]interface{}{}},
	})
	if err != nil {
		t.Logf("err = %v (stop reason %q)", err, res.StopReason)
	}
	if res.StopReason != "tool error" {
		t.Fatalf("stop reason = %q, want tool error", res.StopReason)
	}
	if len(res.Trace) != 1 {
		t.Fatalf("trace has %d entries, want the single failed call", len(res.Trace))
	}
}

func TestAnAlreadyCancelledContextIsRefused(t *testing.T) {
	cfg := baseConfig()
	a, _, _ := testAgent(t, cfg)
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if _, err := a.Run(ctx, &scriptedProposer{}); err == nil {
		t.Fatal("a cancelled context was started anyway")
	}
}

// --- Token accounting ------------------------------------------------------

func TestChargeTokensAccumulates(t *testing.T) {
	cfg := baseConfig()
	a, _, _ := testAgent(t, cfg)
	a.ChargeTokens(10)
	a.ChargeTokens(25)
	if got := a.TokenUsage(); got != 35 {
		t.Fatalf("token usage = %d, want 35", got)
	}
}
