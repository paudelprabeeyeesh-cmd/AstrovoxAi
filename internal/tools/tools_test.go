package tools

import (
	"errors"
	"testing"
	"time"
)

// echoTool is a minimal implementation.
type echoTool struct{}

func (echoTool) Execute(args map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{"echo": args["text"]}, nil
}

// failTool always fails.
type failTool struct{}

func (failTool) Execute(_ map[string]interface{}) (map[string]interface{}, error) {
	return nil, errors.New("boom")
}

// slowTool blocks past any timeout.
type slowTool struct{}

func (slowTool) Execute(_ map[string]interface{}) (map[string]interface{}, error) {
	time.Sleep(2 * time.Second)
	return map[string]interface{}{}, nil
}

func echoSchema(name string, risk Risk) Schema {
	return Schema{
		Name:        name,
		Description: "echoes text",
		Risk:        risk,
		Params: map[string]Param{
			"text": {Kind: KindString, Required: true, MinLength: 1, MaxLength: 64},
		},
		Timeout: time.Second,
	}
}

func testRegistry(t *testing.T) *Registry {
	t.Helper()
	r := New()
	for _, tc := range []struct {
		name string
		risk Risk
	}{{"read.echo", RiskRead}, {"write.echo", RiskWrite}} {
		if err := r.Register(echoSchema(tc.name, tc.risk), echoTool{}); err != nil {
			t.Fatalf("Register(%s) failed: %v", tc.name, err)
		}
	}
	return r
}

// --- Registration ----------------------------------------------------------

func TestRegisterRequiresANameAndATool(t *testing.T) {
	r := New()
	if err := r.Register(Schema{Params: map[string]Param{}}, echoTool{}); err == nil {
		t.Fatal("an unnamed schema was accepted")
	}
	if err := r.Register(echoSchema("x", RiskRead), nil); err == nil {
		t.Fatal("a schema with no tool was accepted")
	}
}

func TestRegisterRejectsADuplicate(t *testing.T) {
	r := New()
	_ = r.Register(echoSchema("a", RiskRead), echoTool{})
	if err := r.Register(echoSchema("a", RiskRead), echoTool{}); err == nil {
		t.Fatal("a duplicate tool was accepted")
	}
}

// --- Validation ------------------------------------------------------------

func TestValidateRejectsAnUnknownTool(t *testing.T) {
	r := testRegistry(t)
	if err := r.Validate(Call{Name: "nope"}); err == nil {
		t.Fatal("an unknown tool passed validation")
	}
}

func TestValidateRejectsAMissingRequiredArgument(t *testing.T) {
	r := testRegistry(t)
	if err := r.Validate(Call{Name: "read.echo", Args: map[string]interface{}{}}); err == nil {
		t.Fatal("a missing required argument passed validation")
	}
}

func TestValidateRejectsAWrongType(t *testing.T) {
	r := testRegistry(t)
	if err := r.Validate(Call{Name: "read.echo", Args: map[string]interface{}{"text": 42}}); err == nil {
		t.Fatal("an integer was accepted for a string argument")
	}
}

func TestValidateRejectsAnUnknownArgument(t *testing.T) {
	// Silently dropping an unknown argument turns "set the path to X" into a
	// call with no path, so it must be refused.
	r := testRegistry(t)
	err := r.Validate(Call{Name: "read.echo", Args: map[string]interface{}{
		"text":  "ok",
		"path":  "/etc/passwd",
		"force": true,
	}})
	if err == nil {
		t.Fatal("unknown arguments were silently dropped")
	}
}

func TestValidateEnforcesLengthAndEnum(t *testing.T) {
	r := New()
	_ = r.Register(Schema{
		Name: "x", Risk: RiskRead, Timeout: time.Second,
		Params: map[string]Param{
			"name": {Kind: KindString, Required: true, MinLength: 2, MaxLength: 4, Enum: []string{"abc"}},
			"n":    {Kind: KindInt, Required: true, MaxLength: 10},
		},
	}, echoTool{})
	if err := r.Validate(Call{Name: "x", Args: map[string]interface{}{"name": "abc", "n": 5}}); err != nil {
		t.Fatalf("a valid call was refused: %v", err)
	}
	if err := r.Validate(Call{Name: "x", Args: map[string]interface{}{"name": "abc", "n": 99}}); err == nil {
		t.Fatal("a too-large integer passed validation")
	}
	if err := r.Validate(Call{Name: "x", Args: map[string]interface{}{"name": "zzz", "n": 1}}); err == nil {
		t.Fatal("a value outside the enum passed validation")
	}
}

func TestValidateAcceptsAJSONRoundTrippedInteger(t *testing.T) {
	// JSON decodes numbers as float64, so a call decoded from a body yields
	// float64. Refusing it would break every real request.
	r := New()
	_ = r.Register(Schema{
		Name: "x", Risk: RiskRead, Timeout: time.Second,
		Params: map[string]Param{"n": {Kind: KindInt, Required: true}},
	}, echoTool{})
	if err := r.Validate(Call{Name: "x", Args: map[string]interface{}{"n": float64(7)}}); err != nil {
		t.Fatalf("a JSON-decoded integer was refused: %v", err)
	}
}

// --- Risk and approval -----------------------------------------------------

func TestOnlyExternalAndIrreversibleNeedApproval(t *testing.T) {
	// Reads and writes are unattended; external and irreversible are not.
	if RiskRead.RequiresApproval() {
		t.Fatal("a read requires approval")
	}
	if RiskWrite.RequiresApproval() {
		t.Fatal("a reversible write requires approval")
	}
	if !RiskExtern.RequiresApproval() {
		t.Fatal("an external action does not require approval")
	}
	if !RiskIrreversible.RequiresApproval() {
		t.Fatal("an irreversible action does not require approval")
	}
}

func TestRequiresApprovalIsTrueForARiskyTool(t *testing.T) {
	r := New()
	_ = r.Register(echoSchema("mail.send", RiskExtern), echoTool{})
	_ = r.Register(echoSchema("note.write", RiskWrite), echoTool{})
	if !r.RequiresApproval(Call{Name: "mail.send"}) {
		t.Fatal("an external tool does not require approval")
	}
	if r.RequiresApproval(Call{Name: "note.write"}) {
		t.Fatal("a reversible write requires approval")
	}
}

// --- Execution and budgets -------------------------------------------------

func TestRunExecutesAValidCall(t *testing.T) {
	r := testRegistry(t)
	e := NewExecutor(r, DefaultBudget())
	res := e.Run(Call{Name: "read.echo", Args: map[string]interface{}{"text": "hi"}})
	if res.Error != "" {
		t.Fatalf("a valid call failed: %s", res.Error)
	}
	if res.Output["echo"] != "hi" {
		t.Fatalf("output = %v, want the echo", res.Output)
	}
}

func TestRunRefusesAnInvalidCallWithoutChargingBudget(t *testing.T) {
	// A model that repeats a bad call would otherwise exhaust the whole run
	// on validation errors.
	r := testRegistry(t)
	e := NewExecutor(r, DefaultBudget())
	for i := 0; i < 10; i++ {
		e.Run(Call{Name: "read.echo", Args: map[string]interface{}{"text": 1}})
	}
	if e.Calls() != 0 {
		t.Fatalf("%d invalid calls were charged against the budget", e.Calls())
	}
}

func TestRunSurfacesAToolFailure(t *testing.T) {
	r := New()
	_ = r.Register(echoSchema("f", RiskRead), failTool{})
	e := NewExecutor(r, DefaultBudget())
	res := e.Run(Call{Name: "f", Args: map[string]interface{}{"text": "x"}})
	if res.Error == "" {
		t.Fatal("a failing tool reported success")
	}
}

func TestRunStopsAfterTheIdenticalCallCap(t *testing.T) {
	// The loop-trap property: a repeated identical call stops rather than
	// looping forever.
	r := testRegistry(t)
	e := NewExecutor(r, Budget{MaxIdenticalCalls: 2, MaxCalls: 100})
	var last *Result
	for i := 0; i < 6; i++ {
		last = e.Run(Call{Name: "read.echo", Args: map[string]interface{}{"text": "same"}})
	}
	if last == nil || !last.Skipped {
		t.Fatal("an identical call repeated beyond the cap without being skipped")
	}
}

func TestDifferentArgumentsAreNotTheSameCall(t *testing.T) {
	r := testRegistry(t)
	e := NewExecutor(r, Budget{MaxIdenticalCalls: 2, MaxCalls: 100})
	for i := 0; i < 5; i++ {
		e.Run(Call{Name: "read.echo", Args: map[string]interface{}{"text": string(rune('a' + i))}})
	}
	if e.Calls() != 5 {
		t.Fatalf("%d calls counted, want 5: distinct arguments were treated as identical", e.Calls())
	}
}

func TestRunStopsAfterTheTotalCallCap(t *testing.T) {
	r := testRegistry(t)
	e := NewExecutor(r, Budget{MaxIdenticalCalls: 100, MaxCalls: 3})
	for i := 0; i < 4; i++ {
		res := e.Run(Call{Name: "read.echo", Args: map[string]interface{}{"text": string(rune('a' + i))}})
		if res.Skipped {
			break
		}
	}
	if e.Calls() != 4 {
		t.Fatalf("%d calls, want the 4th stopped at the cap", e.Calls())
	}
}

func TestRunTimesOutRatherThanHanging(t *testing.T) {
	r := New()
	_ = r.Register(Schema{
		Name: "slow", Risk: RiskRead, Timeout: 100 * time.Millisecond,
		Params: map[string]Param{},
	}, slowTool{})
	e := NewExecutor(r, DefaultBudget())
	start := time.Now()
	res := e.Run(Call{Name: "slow"})
	if time.Since(start) > 2*time.Second {
		t.Fatal("a slow tool hung the executor")
	}
	if res.Error == "" || !res.Skipped && res.Error == "" {
		t.Log("timeout reported as:", res.Error)
	}
	if !stringsContains(res.Error, "timeout") {
		t.Fatalf("error = %q, want a timeout", res.Error)
	}
}

func TestNamesIsSortedAndDeterministic(t *testing.T) {
	// A prompt built from the catalogue must be stable across runs, or the
	// eval set is not reproducible.
	r := New()
	for _, n := range []string{"z.read", "a.read", "m.read"} {
		_ = r.Register(echoSchema(n, RiskRead), echoTool{})
	}
	names := r.Names()
	if len(names) != 3 || names[0] != "a.read" || names[1] != "m.read" || names[2] != "z.read" {
		t.Fatalf("names = %v, want sorted", names)
	}
}

func TestFingerprintSeparatesArguments(t *testing.T) {
	a := Fingerprint(Call{Name: "t", Args: map[string]interface{}{"x": "1", "y": "2"}})
	b := Fingerprint(Call{Name: "t", Args: map[string]interface{}{"y": "2", "x": "1"}})
	if a != b {
		t.Fatal("the fingerprint depends on argument order, which it must not")
	}
	c := Fingerprint(Call{Name: "t", Args: map[string]interface{}{"x": "1", "y": "3"}})
	if a == c {
		t.Fatal("different arguments produced the same fingerprint")
	}
}

// stringsContains avoids importing strings in this test file.
func stringsContains(s, sub string) bool {
	if len(sub) == 0 {
		return true
	}
	for i := 0; i+len(sub) <= len(s); i++ {
		if s[i:i+len(sub)] == sub {
			return true
		}
	}
	return false
}
