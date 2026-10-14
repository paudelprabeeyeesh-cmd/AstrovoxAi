package tools

import (
	"context"
	"strings"
	"testing"
	"time"
)

// ---------------------------------------------------------------------------
// D-004: approval gates and recorded decisions
// ---------------------------------------------------------------------------

func gatedSchema(name string, actions ...Action) Schema {
	return Schema{
		Name: name, Description: name + ".", Risk: RiskIrreversible,
		Actions: actions, Timeout: time.Second,
		// `amount` is declared so the call below is accepted by validation and
		// the refusal comes from the approval gate. With no parameter declared
		// the call is rejected earlier as an unknown argument, which makes the
		// test pass for the wrong reason.
		Params: map[string]Param{"amount": {Kind: KindInt, Required: true}},
	}
}

func purchaseCall() Call {
	return Call{Name: "purchase", Args: map[string]interface{}{"amount": 100}}
}

func TestGatedActionsRequireADecision(t *testing.T) {
	// A benign-looking risk next to a gated action must not bypass the gate.
	r := New()
	ran := false
	err := r.Register(gatedSchema("purchase", ActionPurchase), implTool(func(args map[string]interface{}) (map[string]interface{}, error) {
		ran = true
		return map[string]interface{}{}, nil
	}))
	if err != nil {
		t.Fatal(err)
	}

	gate := NewApprovalGate(time.Minute, nil)
	executor := NewExecutor(r, DefaultBudget())
	executor.SetApprover(gate)

	res := executor.Run(purchaseCall())
	if ran || !res.Skipped {
		t.Fatal("a purchase ran with no decision recorded")
	}
	if !strings.Contains(res.Error, "approval") {
		t.Fatalf("the refusal does not explain itself: %q", res.Error)
	}
}

func TestAGrantedCallRunsAndTheGrantExpires(t *testing.T) {
	r := New()
	ran := false
	err := r.Register(gatedSchema("purchase", ActionPurchase), implTool(func(args map[string]interface{}) (map[string]interface{}, error) {
		ran = true
		return map[string]interface{}{}, nil
	}))
	if err != nil {
		t.Fatal(err)
	}

	now := time.Now()
	gate := NewApprovalGate(time.Minute, func() time.Time { return now })
	executor := NewExecutor(r, DefaultBudget())
	executor.SetApprover(gate)

	call := purchaseCall()
	if _, err := gate.Grant(call, schemaActions("purchase"), "alice", "approved"); err != nil {
		t.Fatal(err)
	}
	if res := executor.Run(call); !ran || res.Error != "" {
		t.Fatalf("the granted call did not run: %+v", res)
	}
}

func TestAnExpiredGrantRefusesTheCall(t *testing.T) {
	// A grant with no expiry is how a one-off decision becomes permanent
	// permission.
	now := time.Now()
	gate := NewApprovalGate(time.Minute, func() time.Time { return now })

	call := purchaseCall()
	if _, err := gate.Grant(call, schemaActions("purchase"), "alice", "one-off"); err != nil {
		t.Fatal(err)
	}
	// A later clock: the grant has aged out.
	now = now.Add(2 * time.Minute)
	if err := gate.Approve(call, gatedSchema("purchase", ActionPurchase)); err == nil {
		t.Fatal("an expired grant still authorised a call")
	}
}

func TestADeniedGrantRefusesTheCall(t *testing.T) {
	gate := NewApprovalGate(time.Minute, nil)
	call := purchaseCall()
	if _, err := gate.Deny(call, schemaActions("purchase"), "alice", "budget exceeded"); err != nil {
		t.Fatal(err)
	}
	if err := gate.Approve(call, gatedSchema("purchase", ActionPurchase)); err == nil {
		t.Fatal("a denied decision authorised a call")
	}
}

func TestAnUndecidedCallIsRefused(t *testing.T) {
	// The default is a refusal: a request that was never answered must not
	// become an allowance.
	gate := NewApprovalGate(time.Minute, nil)
	call := purchaseCall()
	if err := gate.Approve(call, gatedSchema("purchase", ActionPurchase)); err == nil {
		t.Fatal("a call with no decision ran")
	}
}

func TestAGrantIsBoundToTheExactArguments(t *testing.T) {
	gate := NewApprovalGate(time.Minute, nil)
	approved := Call{Name: "purchase", Args: map[string]interface{}{"amount": 100}}
	if _, err := gate.Grant(approved, schemaActions("purchase"), "alice", "ok"); err != nil {
		t.Fatal(err)
	}

	other := Call{Name: "purchase", Args: map[string]interface{}{"amount": 99999}}
	if err := gate.Approve(other, gatedSchema("purchase", ActionPurchase)); err == nil {
		t.Fatal("a grant for one amount authorised a different amount")
	}
}

func TestADecisionNeedsAnApprover(t *testing.T) {
	// A decision with no actor cannot be reviewed.
	gate := NewApprovalGate(time.Minute, nil)
	if _, err := gate.Grant(purchaseCall(), schemaActions("purchase"), "", "why"); err == nil {
		t.Fatal("a decision with no approver was recorded")
	}
}

func TestDenialsAreRecordedAlongsideGrants(t *testing.T) {
	// A gate that records only its grants cannot answer "who refused and why".
	gate := NewApprovalGate(time.Minute, nil)
	if _, err := gate.Deny(purchaseCall(), schemaActions("purchase"), "alice", "policy"); err != nil {
		t.Fatal(err)
	}
	decisions := gate.Decisions("")
	if len(decisions) != 1 {
		t.Fatalf("decisions = %d, want the denial recorded", len(decisions))
	}
	if decisions[0].Granted {
		t.Fatal("a denial was recorded as a grant")
	}
}

func TestRevocationRefusesTheCall(t *testing.T) {
	gate := NewApprovalGate(time.Minute, nil)
	call := purchaseCall()
	if _, err := gate.Grant(call, schemaActions("purchase"), "alice", "ok"); err != nil {
		t.Fatal(err)
	}
	if err := gate.Revoke(Fingerprint(call), "alice", "budget cut"); err != nil {
		t.Fatal(err)
	}
	if err := gate.Approve(call, gatedSchema("purchase", ActionPurchase)); err == nil {
		t.Fatal("a revoked grant still authorised a call")
	}

	// The revocation is recorded as a separate entry, not an edit of the grant.
	counts := gate.Counts()
	if counts["revoked"] != 1 || counts["granted"] != 1 {
		t.Fatalf("revocation did not keep the original grant: %v", counts)
	}
}

func TestAuditDecisionsFilterByApprover(t *testing.T) {
	gate := NewApprovalGate(time.Minute, nil)
	if _, err := gate.Grant(purchaseCall(), schemaActions("purchase"), "alice", "ok"); err != nil {
		t.Fatal(err)
	}
	if _, err := gate.Deny(purchaseCall(), schemaActions("purchase"), "bob", "no"); err != nil {
		t.Fatal(err)
	}
	if got := len(gate.Decisions("bob")); got != 1 {
		t.Fatalf("bob's decisions = %d, want 1", got)
	}
	if got := len(gate.Decisions("")); got != 2 {
		t.Fatalf("all decisions = %d, want both", got)
	}
}

func TestReadsAreNotGated(t *testing.T) {
	r := New()
	ran := false
	err := r.Register(Schema{Name: "lookup", Risk: RiskRead, Timeout: time.Second,
		Actions: []Action{ActionRead}, Params: map[string]Param{}},
		implTool(func(args map[string]interface{}) (map[string]interface{}, error) {
			ran = true
			return map[string]interface{}{}, nil
		}))
	if err != nil {
		t.Fatal(err)
	}
	gate := NewApprovalGate(time.Minute, nil)
	executor := NewExecutor(r, DefaultBudget())
	executor.SetApprover(gate)
	executor.Run(Call{Name: "lookup", Args: map[string]interface{}{}})
	if !ran {
		t.Fatal("a read was gated on approval")
	}
}

func TestEveryGatedActionBlocksTheCall(t *testing.T) {
	for a := range gatedActions {
		r := New()
		ran := false
		schema := Schema{Name: "t", Risk: RiskWrite, Actions: []Action{a}, Timeout: time.Second, Params: map[string]Param{}}
		if err := r.Register(schema, implTool(func(map[string]interface{}) (map[string]interface{}, error) {
			ran = true
			return map[string]interface{}{}, nil
		})); err != nil {
			t.Fatal(err)
		}

		gate := NewApprovalGate(time.Minute, nil)
		executor := NewExecutor(r, DefaultBudget())
		executor.SetApprover(gate)
		executor.Run(Call{Name: "t", Args: map[string]interface{}{}})
		if ran {
			t.Fatalf("action %s ran unattended even though risk was write", a)
		}
	}
}

// ---------------------------------------------------------------------------
// D-006: recording, replay, and redaction
// ---------------------------------------------------------------------------

func TestARunIsRecordedAndReplayable(t *testing.T) {
	r, executor := newLoopFixture(t)
	thinker := &scriptedThinker{actions: []action{
		callNow("echo", map[string]interface{}{"text": "one"}),
		replyNow("the answer"),
	}}

	loop := NewLoop(r, executor, thinker.Think, DefaultLimits())
	outcome := loop.Run(context.Background(), "do work")

	recorder := NewRunRecorder()
	summary := recorder.Record(outcome, "do work")

	replay, err := recorder.Replay(summary.RunID)
	if err != nil {
		t.Fatalf("replay failed: %v", err)
	}
	if replay.Answer != "the answer" {
		t.Fatalf("replayed answer = %q", replay.Answer)
	}
	if replay.ToolCalls != outcome.ToolCalls {
		t.Fatalf("replay lost tool calls: %d vs %d", replay.ToolCalls, outcome.ToolCalls)
	}
}

func TestRecordingRedactsSecrets(t *testing.T) {
	// A record containing a credential is a credential in the repo, so
	// redaction happens on write.
	r := New()
	err := r.Register(Schema{Name: "cfg", Risk: RiskRead, Timeout: time.Second, Params: map[string]Param{}},
		implTool(func(args map[string]interface{}) (map[string]interface{}, error) {
			return map[string]interface{}{"blob": "token sk-abcdefghijklmnop1234 here"}, nil
		}))
	if err != nil {
		t.Fatal(err)
	}

	thinker := &scriptedThinker{actions: []action{
		callNow("cfg", map[string]interface{}{}),
		replyNow("done"),
	}}
	executor := NewExecutor(r, DefaultBudget())
	loop := NewLoop(r, executor, thinker.Think, DefaultLimits())
	outcome := loop.Run(context.Background(), "leak the config")

	recorder := NewRunRecorder()
	summary := recorder.Record(outcome, "leak the config")
	if summary.Redactions == 0 {
		t.Fatal("a credential in the tool output was recorded verbatim")
	}

	rec, _ := recorder.Get(summary.RunID)
	rendered := ""
	for _, turn := range rec.Turns {
		for _, v := range turn.Output {
			if s, ok := v.(string); ok {
				rendered += s
			}
		}
	}
	if strings.Contains(rendered, "sk-abcdefghijklmnop1234") {
		t.Fatal("the credential survived into the stored record")
	}
}

func TestRedactorDetectsAndRemovesCredentialShapes(t *testing.T) {
	for _, secret := range []string{
		"sk-abcdefghijklmnop1234",
		"AKIAIOSFODNN7EXAMPLE",
		"ghp_16C7e42F292c6912E7710c838347Ae178B4a",
		"xoxb-1234567890-abcdefghijklmnop",
		"glpat-abcdefghijklmnopqrstuvwx",
	} {
		if !DefaultRedactor.ContainsSecret(secret) {
			t.Fatalf("a credential shape was not detected: %s", secret)
		}
		if got := DefaultRedactor.Redact(secret); strings.Contains(got, secret) {
			t.Fatalf("the credential survived redaction: %s", secret)
		}
	}
}

func TestRedactorIgnoresOrdinaryText(t *testing.T) {
	if DefaultRedactor.ContainsSecret("a plain log line about a user") {
		t.Fatal("ordinary text was flagged as a credential")
	}
}

func TestRedactorRemovesAPrivateKeyBlock(t *testing.T) {
	key := "-----BEGIN RSA PRIVATE KEY-----\nabcd\n-----END RSA PRIVATE KEY-----"
	if got := DefaultRedactor.Redact(key); strings.Contains(got, "PRIVATE KEY") {
		t.Fatalf("a private key block survived redaction: %q", got)
	}
}

func TestReplayOfAnUnknownRunFails(t *testing.T) {
	if _, err := NewRunRecorder().Replay("missing"); err == nil {
		t.Fatal("replaying an unknown run produced an outcome")
	}
}

func TestAuditCombinesDecisionsAndRuns(t *testing.T) {
	// An operator asking "why did this happen" needs the decision and the run
	// together; two logs that cannot be correlated are one log split in half.
	gate := NewApprovalGate(time.Minute, nil)
	recorder := NewRunRecorder()
	audit := NewAudit(gate, recorder)

	if _, err := gate.Grant(purchaseCall(), schemaActions("purchase"), "alice", "ok"); err != nil {
		t.Fatal(err)
	}
	r, executor := newLoopFixture(t)
	thinker := &scriptedThinker{actions: []action{replyNow("fine")}}
	loop := NewLoop(r, executor, thinker.Think, DefaultLimits())
	recorder.Record(loop.Run(context.Background(), "work"), "work")

	timeline := audit.Timeline(0)
	sawApproval, sawRun := false, false
	for _, entry := range timeline {
		switch entry.Action {
		case "approval":
			sawApproval = true
		case "run":
			sawRun = true
		}
	}
	if !sawApproval || !sawRun {
		t.Fatalf("the audit is missing half the record: %v", timeline)
	}
	if counts := audit.Summary(); counts["runs"] != 1 || counts["granted"] != 1 {
		t.Fatalf("audit summary = %v", counts)
	}
}

func TestAuditTimelineRespectsLimit(t *testing.T) {
	gate := NewApprovalGate(time.Minute, nil)
	if _, err := gate.Grant(purchaseCall(), schemaActions("purchase"), "a", "ok"); err != nil {
		t.Fatal(err)
	}
	audit := NewAudit(gate, NewRunRecorder())
	if got := len(audit.Timeline(1)); got != 1 {
		t.Fatalf("timeline limit ignored: %d entries", got)
	}
}

// schemaActions returns the actions a schema declares, mirroring what the
// executor would ask for.
func schemaActions(name string) []Action {
	switch name {
	case "purchase":
		return []Action{ActionPurchase}
	default:
		return []Action{ActionIrreversible}
	}
}
