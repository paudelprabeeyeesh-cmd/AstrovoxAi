package agent

import (
	"context"
	"testing"

	"github.com/astrovox/astrovox/internal/tools"
)

// TestDebugBudget was originally a scratch debugging file. It is kept as a
// regression test: the agent's approver decision must reach the executor,
// so an approved external call runs instead of being refused by the
// executor's default deny approver, and the agent's own limits still apply.
func TestDebugBudget(t *testing.T) {
	cfg := baseConfig()
	cfg.Approver = AutoApprover{}
	a, _, exec := testAgent(t, cfg)

	if a.cfg.Limits.MaxSteps <= 0 {
		t.Fatalf("agent limits not defaulted: %+v", a.cfg.Limits)
	}
	if b := exec.BudgetConfig(); b.MaxCalls <= 0 || b.MaxIdenticalCalls <= 0 {
		t.Fatalf("executor budget not set: %+v", b)
	}

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
	if len(res.Trace) != 1 {
		t.Fatalf("trace has %d entries, want 1", len(res.Trace))
	}
	if res.Trace[0].Skipped {
		t.Fatal("the approved call was skipped: the agent approver did not reach the executor")
	}
	if exec.Calls() != 1 {
		t.Fatalf("executor calls = %d, want 1", exec.Calls())
	}
}
