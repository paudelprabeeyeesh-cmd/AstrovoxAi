package tools

import (
	"errors"
	"strings"
	"testing"
	"time"
)

// echoImpl is a trivial tool for exercising the executor.
type echoImpl struct{ ran bool }

func (e *echoImpl) Execute(args map[string]interface{}) (map[string]interface{}, error) {
	e.ran = true
	return map[string]interface{}{"echo": args["text"]}, nil
}

// hangImpl sleeps past the schema timeout, for the timeout path.
type hangImpl struct{}

func (hangImpl) Execute(args map[string]interface{}) (map[string]interface{}, error) {
	time.Sleep(2 * time.Second)
	return map[string]interface{}{}, nil
}

// loudImpl returns an unbounded payload, for the output cap.
type loudImpl struct{}

func (loudImpl) Execute(args map[string]interface{}) (map[string]interface{}, error) {
	big := strings.Repeat("x", 10_000)
	return map[string]interface{}{"data": big}, nil
}

func echoImplSchema() Schema {
	return Schema{
		Name:        "echo",
		Description: "Echo the text back.",
		Risk:        RiskRead,
		Timeout:     5 * time.Second,
		Params: map[string]Param{
			"text": {Kind: KindString, Required: true, MaxLength: 100},
		},
	}
}

// ---------------------------------------------------------------------------
// D-001: generated docs
// ---------------------------------------------------------------------------

func TestCatalogueListsEveryToolWithItsSchema(t *testing.T) {
	r := New()
	if err := r.Register(echoImplSchema(), &echoImpl{}); err != nil {
		t.Fatal(err)
	}

	catalogue := r.Catalogue()
	if !strings.Contains(catalogue, "echo") {
		t.Fatalf("catalogue does not name the tool: %q", catalogue)
	}
	if !strings.Contains(catalogue, "Echo the text back.") {
		t.Fatal("catalogue drops the description, so a model cannot choose between tools")
	}
	if !strings.Contains(catalogue, "text") {
		t.Fatal("catalogue drops the parameter name, so a model cannot form arguments")
	}
}

func TestCatalogueMarksRequiredParameters(t *testing.T) {
	r := New()
	if err := r.Register(echoImplSchema(), &echoImpl{}); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(r.Catalogue(), "required") {
		t.Fatal("a required parameter is not distinguishable from an optional one")
	}
}

func TestCatalogueIsDeterministic(t *testing.T) {
	// The catalogue goes into a prompt, so two builds must agree or an eval's
	// prompt changes between runs for no reason.
	r := New()
	if err := r.Register(echoImplSchema(), &echoImpl{}); err != nil {
		t.Fatal(err)
	}
	if err := r.Register(Schema{Name: "delete", Description: "Delete.", Risk: RiskIrreversible, Timeout: time.Second}, &echoImpl{}); err != nil {
		t.Fatal(err)
	}
	first, second := r.Catalogue(), r.Catalogue()
	if first != second {
		t.Fatalf("catalogue changed between builds:\n%s\n%s", first, second)
	}
}

// ---------------------------------------------------------------------------
// D-002: output caps and approval enforcement
// ---------------------------------------------------------------------------

func TestUnapprovedIrreversibleCallIsRefused(t *testing.T) {
	// ErrApprovalRequired and RequiresApproval already existed; the executor
	// never consulted either, so every tool ran unattended.
	r := New()
	ran := false
	tool := implTool(func(args map[string]interface{}) (map[string]interface{}, error) {
		ran = true
		return map[string]interface{}{}, nil
	})
	err := r.Register(Schema{
		Name: "drop-table", Description: "Drop a table.", Risk: RiskIrreversible, Timeout: time.Second,
	}, tool)
	if err != nil {
		t.Fatal(err)
	}

	executor := NewExecutor(r, DefaultBudget())
	res := executor.Run(Call{Name: "drop-table", Args: map[string]interface{}{}})

	if ran {
		t.Fatal("an irreversible tool was executed without approval")
	}
	if !res.Skipped {
		t.Fatalf("the refusal is not marked as skipped: %+v", res)
	}
	if !strings.Contains(res.Error, "approval") {
		t.Fatalf("the refusal does not explain itself: %q", res.Error)
	}
}

func TestApprovedIrreversibleCallRuns(t *testing.T) {
	r := New()
	ran := false
	err := r.Register(Schema{Name: "drop-table", Description: "Drop.", Risk: RiskIrreversible, Timeout: time.Second},
		implTool(func(args map[string]interface{}) (map[string]interface{}, error) {
			ran = true
			return map[string]interface{}{"dropped": true}, nil
		}))
	if err != nil {
		t.Fatal(err)
	}

	executor := NewExecutor(r, DefaultBudget())
	executor.GrantApproval(Call{Name: "drop-table", Args: map[string]interface{}{}})

	res := executor.Run(Call{Name: "drop-table", Args: map[string]interface{}{}})
	if !ran {
		t.Fatal("the approved call did not run")
	}
	if res.Error != "" {
		t.Fatalf("an approved call failed: %q", res.Error)
	}
}

func TestApprovalIsBoundToTheExactCall(t *testing.T) {
	// A grant for one argument set must not authorise a different one: the
	// whole point of a decision is that it is about a specific action.
	r := New()
	err := r.Register(Schema{
		Name: "send-email", Description: "Send.", Risk: RiskIrreversible, Timeout: time.Second,
		Params: map[string]Param{"to": {Kind: KindString, Required: true}},
	}, implTool(func(args map[string]interface{}) (map[string]interface{}, error) {
		return map[string]interface{}{}, nil
	}))
	if err != nil {
		t.Fatal(err)
	}

	executor := NewExecutor(r, DefaultBudget())
	executor.GrantApproval(Call{Name: "send-email", Args: map[string]interface{}{"to": "alice@example.com"}})

	res := executor.Run(Call{Name: "send-email", Args: map[string]interface{}{"to": "mallory@evil.invalid"}})
	if !res.Skipped {
		t.Fatal("an approval for one recipient authorised a different recipient")
	}
}

func TestOutputIsCapped(t *testing.T) {
	r := New()
	err := r.Register(Schema{Name: "noisy", Description: "Returns a lot.", Risk: RiskRead, Timeout: time.Second}, loudImpl{})
	if err != nil {
		t.Fatal(err)
	}

	budget := DefaultBudget()
	budget.MaxOutputBytes = 1000
	executor := NewExecutor(r, budget)

	res := executor.Run(Call{Name: "noisy", Args: map[string]interface{}{}})
	if res.Error != "" {
		t.Fatalf("the call failed: %q", res.Error)
	}
	data, _ := res.Output["data"].(string)
	if len(data) > 1000 {
		t.Fatalf("output is %d bytes, above the 1000-byte cap", len(data))
	}
	if !strings.Contains(data, "truncated") {
		t.Fatal("a truncated output does not say so, so a caller cannot tell quality from cap")
	}
}

func TestOutputWithinTheCapIsUntouched(t *testing.T) {
	r := New()
	err := r.Register(echoImplSchema(), &echoImpl{})
	if err != nil {
		t.Fatal(err)
	}
	executor := NewExecutor(r, DefaultBudget())
	res := executor.Run(Call{Name: "echo", Args: map[string]interface{}{"text": "short"}})
	if got := res.Output["echo"]; got != "short" {
		t.Fatalf("output was altered: %v", got)
	}
}

func TestATimeoutIsAResultNotAHang(t *testing.T) {
	r := New()
	err := r.Register(Schema{Name: "block", Description: "Blocks.", Risk: RiskRead, Timeout: 100 * time.Millisecond}, hangImpl{})
	if err != nil {
		t.Fatal(err)
	}

	executor := NewExecutor(r, DefaultBudget())
	start := time.Now()
	res := executor.Run(Call{Name: "block", Args: map[string]interface{}{}})
	if time.Since(start) > 2*time.Second {
		t.Fatal("a timeout did not bound the call")
	}
	if !strings.Contains(res.Error, "timeout") {
		t.Fatalf("the timeout is not explained: %q", res.Error)
	}
}

func TestReadingToolNeedsNoApproval(t *testing.T) {
	// A read is unattended; gating one would make every agent unusable.
	r := New()
	ran := false
	err := r.Register(echoImplSchema(), implTool(func(args map[string]interface{}) (map[string]interface{}, error) {
		ran = true
		return map[string]interface{}{}, nil
	}))
	if err != nil {
		t.Fatal(err)
	}
	executor := NewExecutor(r, DefaultBudget())
	executor.Run(Call{Name: "echo", Args: map[string]interface{}{"text": "hi"}})
	if !ran {
		t.Fatal("a read tool was gated on approval")
	}
}

func TestExternalRiskIsGated(t *testing.T) {
	r := New()
	ran := false
	err := r.Register(Schema{Name: "notify", Description: "Send outbound.", Risk: RiskExtern, Timeout: time.Second},
		implTool(func(args map[string]interface{}) (map[string]interface{}, error) {
			ran = true
			return map[string]interface{}{}, nil
		}))
	if err != nil {
		t.Fatal(err)
	}
	executor := NewExecutor(r, DefaultBudget())
	res := executor.Run(Call{Name: "notify", Args: map[string]interface{}{}})
	if ran || !res.Skipped {
		t.Fatal("an external action ran unattended")
	}
}

func TestWriteRiskRunsUnattended(t *testing.T) {
	// A write is reversible by contract, so gating it would halt the agent on
	// every reversible change.
	r := New()
	ran := false
	err := r.Register(Schema{Name: "save", Description: "Save.", Risk: RiskWrite, Timeout: time.Second},
		implTool(func(args map[string]interface{}) (map[string]interface{}, error) {
			ran = true
			return map[string]interface{}{}, nil
		}))
	if err != nil {
		t.Fatal(err)
	}
	executor := NewExecutor(r, DefaultBudget())
	executor.Run(Call{Name: "save", Args: map[string]interface{}{}})
	if !ran {
		t.Fatal("a reversible write was gated on approval")
	}
}

func TestValidationRunsBeforeTheBudget(t *testing.T) {
	// A model repeating a bad call must not exhaust the run on validation
	// errors, so a refused call is not charged.
	r := New()
	if err := r.Register(echoImplSchema(), &echoImpl{}); err != nil {
		t.Fatal(err)
	}
	executor := NewExecutor(r, DefaultBudget())
	for i := 0; i < 20; i++ {
		executor.Run(Call{Name: "echo", Args: map[string]interface{}{}}) // missing required arg
	}
	if got := executor.Calls(); got != 0 {
		t.Fatalf("invalid calls were charged against the budget: %d", got)
	}
}

func TestUnknownToolIsAResultNotAPanic(t *testing.T) {
	r := New()
	executor := NewExecutor(r, DefaultBudget())
	res := executor.Run(Call{Name: "ghost", Args: map[string]interface{}{}})
	if res.Error == "" {
		t.Fatal("an unknown tool produced no error")
	}
	if got := executor.Calls(); got != 0 {
		t.Fatalf("an unknown tool consumed budget: %d", got)
	}
}

func TestASlowToolDoesNotBlockTheExecutorForOthers(t *testing.T) {
	// Isolation: one slow tool must not hold the executor's lock, or a second
	// caller of a different tool waits on it.
	r := New()
	if err := r.Register(echoImplSchema(), &echoImpl{}); err != nil {
		t.Fatal(err)
	}
	if err := r.Register(Schema{Name: "block", Description: "Blocks.", Risk: RiskRead, Timeout: 5 * time.Second}, hangImpl{}); err != nil {
		t.Fatal(err)
	}

	executor := NewExecutor(r, DefaultBudget())
	done := make(chan *Result, 1)
	go func() { done <- executor.Run(Call{Name: "block", Args: map[string]interface{}{}}) }()

	time.Sleep(50 * time.Millisecond)
	fast := executor.Run(Call{Name: "echo", Args: map[string]interface{}{"text": "hi"}})
	if fast.Error != "" {
		t.Fatalf("a fast tool was blocked by a slow one: %q", fast.Error)
	}
	<-done
}

// implTool adapts a closure to Tool.
type implTool func(args map[string]interface{}) (map[string]interface{}, error)

func (f implTool) Execute(args map[string]interface{}) (map[string]interface{}, error) {
	return f(args)
}

var _ = errors.New
