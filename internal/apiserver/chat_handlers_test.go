package apiserver

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/astrovox/astrovox/internal/chat"
)

// chatServer returns a server with a deterministic vendor and a spend gate.
// The budget is large enough that the small fixture requests are not
// refused; the refusal behaviour has its own tests.
func chatServer(t *testing.T) (*Server, *Vendor, *SpendGate) {
	t.Helper()
	vendor := &Vendor{
		Chunks:        []string{"The answer ", "is 42."},
		UsageToReport: chat.Usage{InputTokens: 10, OutputTokens: 5},
	}
	gate := NewSpendGate(10.0)
	s, err := New(Config{JWTSecret: "chat-test-secret"})
	if err != nil {
		t.Fatalf("New failed: %v", err)
	}
	// Replace the provider attachChat installed so the test controls it.
	o, err := chat.New(vendor, gate, chat.WithSystemPrompt("You are a test assistant."))
	if err != nil {
		t.Fatalf("chat.New failed: %v", err)
	}
	s.orchestrator = o
	s.spend = gate
	return s, vendor, gate
}

func postJSON(t *testing.T, s *Server, token, body string) *httptest.ResponseRecorder {
	t.Helper()
	return call(t, s, "POST", "/chat/message", body, token)
}

func TestMessageRequiresAToken(t *testing.T) {
	s, _, _ := chatServer(t)
	rec := postJSON(t, s, "", `{"text":"hi"}`)
	if rec.Code != http.StatusForbidden {
		t.Fatalf("status = %d, want 403", rec.Code)
	}
}

func TestMessageRequiresText(t *testing.T) {
	s, _, _ := chatServer(t)
	token, _ := registerAndToken(t, s)
	rec := postJSON(t, s, token, `{"model":"gpt-4o"}`)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400: %s", rec.Code, rec.Body.String())
	}
}

func TestMessageReturnsTheProviderAnswer(t *testing.T) {
	s, _, _ := chatServer(t)
	token, _ := registerAndToken(t, s)
	rec := postJSON(t, s, token, `{"text":"what is the answer?","model":"gpt-4o"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200: %s", rec.Code, rec.Body.String())
	}
	var body struct {
		Status int `json:"status"`
		Data   struct {
			Answer string `json:"answer"`
			Model  string `json:"model"`
			Usage  struct {
				InputTokens  int `json:"input_tokens"`
				OutputTokens int `json:"output_tokens"`
			} `json:"usage"`
		} `json:"data"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("response is not JSON: %v", err)
	}
	if body.Data.Answer != "The answer is 42." {
		t.Fatalf("answer = %q, want the concatenation of the stream chunks", body.Data.Answer)
	}
	if body.Data.Usage.InputTokens != 10 {
		t.Fatalf("input tokens = %d, want the provider's count", body.Data.Usage.InputTokens)
	}
}

func TestMessageInjectsTheCallersMemory(t *testing.T) {
	s, vendor, _ := chatServer(t)
	token, _ := registerAndToken(t, s)

	// The caller's stored memory must reach the provider, so a memory the
	// user ever saved is actually used.
	if rec := call(t, s, "POST", "/memory", `{"text":"I prefer tea"}`, token); rec.Code != http.StatusCreated {
		t.Fatalf("save memory status = %d, want 201", rec.Code)
	}
	postJSON(t, s, token, `{"text":"hi"}`)

	if vendor.lastReq == nil {
		t.Fatal("the provider was never called")
	}
	found := false
	for _, m := range vendor.lastReq.Messages {
		if strings.Contains(m.Content, "I prefer tea") {
			found = true
		}
	}
	if !found {
		t.Fatalf("memory was not injected into the prompt: %+v", vendor.lastReq.Messages)
	}
}

func TestMessageIgnoresACallerSuppliedMemory(t *testing.T) {
	// Only the store may supply memory. A body-supplied list would let a
	// caller inject arbitrary context that bypasses the policy screen.
	vendor := &Vendor{Chunks: []string{"ok"}}
	gate := NewSpendGate(1)
	o, _ := chat.New(vendor, gate)
	s, _ := New(Config{JWTSecret: "s"})
	s.orchestrator = o
	s.spend = gate
	token, _ := registerAndToken(t, s)

	postJSON(t, s, token, `{"text":"hi","memory":["forged context"]}`)
	for _, m := range vendor.lastReq.Messages {
		if strings.Contains(m.Content, "forged context") {
			t.Fatal("a caller-supplied memory list reached the provider")
		}
	}
}

func TestMessageSurfacesAProviderFailure(t *testing.T) {
	s, _, _ := chatServer(t)
	// The vendor is replaced by the installed one, so install again with a
	// failing provider.
	vendor := &Vendor{FailCall: true}
	o, _ := chat.New(vendor, NewSpendGate(1))
	s.orchestrator = o
	token, _ := registerAndToken(t, s)
	rec := postJSON(t, s, token, `{"text":"hi"}`)
	if rec.Code == http.StatusOK {
		t.Fatal("a provider failure was reported as a success")
	}
	// The failure must not carry the internal message.
	if strings.Contains(rec.Body.String(), "upstream") {
		t.Fatal("internal provider detail leaked into the response")
	}
}

func TestMessageSurfacesAMidStreamFailure(t *testing.T) {
	// A broken stream must not produce a partial answer that reads as
	// complete.
	vendor := &Vendor{FailStream: true}
	o, _ := chat.New(vendor, NewSpendGate(1))
	s, _ := New(Config{JWTSecret: "s"})
	s.orchestrator = o
	token, _ := registerAndToken(t, s)
	rec := postJSON(t, s, token, `{"text":"hi"}`)
	if rec.Code == http.StatusOK {
		t.Fatal("a broken stream produced a 200")
	}
}

func TestSpendCapRefusesBeforeTheProviderCall(t *testing.T) {
	vendor := &Vendor{Chunks: []string{"ok"}}
	// A zero budget, so any call is refused.
	gate := NewSpendGate(0.0000001)
	o, _ := chat.New(vendor, gate)
	s, _ := New(Config{JWTSecret: "s"})
	s.orchestrator = o
	token, _ := registerAndToken(t, s)

	rec := postJSON(t, s, token, `{"text":"hi","model":"gpt-4"}`)
	if rec.Code != http.StatusTooManyRequests {
		t.Fatalf("status = %d, want 429 when the budget is exhausted", rec.Code)
	}
	if vendor.lastReq != nil {
		t.Fatal("the provider was called after the spend gate refused")
	}
}

func TestSpendCapIsPerUser(t *testing.T) {
	// The estimate is promptTokens * price + maxOutputTokens * price. With
	// gpt-4 at 0.03/1K in and 0.06/1K out and maxOutputTokens defaulting to
	// 1024, one call is roughly $0.06, so a budget of $0.10 allows one call
	// per user. If the cap were global, A's spend would push the total over
	// the limit and B would be refused.
	gate := NewSpendGate(0.10)
	o, _ := chat.New(&Vendor{Chunks: []string{"ok"}, UsageToReport: chat.Usage{InputTokens: 10, OutputTokens: 5}}, gate)
	s, _ := New(Config{JWTSecret: "s"})
	s.orchestrator = o
	s.spend = gate
	tokA, dataA := registerAndToken(t, s)
	tokB, _ := registerAndToken(t, s)

	subjectA := dataA["account"].(map[string]interface{})["id"].(string)

	first := postJSON(t, s, tokA, `{"text":"hi","model":"gpt-4"}`)
	if first.Code != http.StatusOK {
		t.Fatalf("the first call was refused: %s", first.Body.String())
	}
	spentA := gate.Spend(subjectA)
	if spentA <= 0 {
		t.Fatalf("the first call was not metered for %s: %v", subjectA, gate.spend)
	}

	second := postJSON(t, s, tokB, `{"text":"hi","model":"gpt-4"}`)
	if second.Code == http.StatusTooManyRequests {
		t.Fatalf(
			"user B was blocked (%s spent $%.4f, limit $%.2f): the cap is global, not per user",
			subjectA, spentA, gate.DailyLimitUSD,
		)
	}
}

func TestUsageReportsTheMeteredSpend(t *testing.T) {
	s, _, gate := chatServer(t)
	token, _ := registerAndToken(t, s)
	postJSON(t, s, token, `{"text":"hi"}`)

	rec := call(t, s, "GET", "/chat/usage", "", token)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200: %s", rec.Code, rec.Body.String())
	}
	var body struct {
		Data struct {
			SpendUSD  float64 `json:"spend_usd"`
			Remaining float64 `json:"remaining_usd"`
		} `json:"data"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("response is not JSON: %v", err)
	}
	if body.Data.SpendUSD <= 0 {
		t.Fatal("the usage endpoint reports zero spend for a completed call")
	}
	if body.Data.Remaining < 0 {
		t.Fatal("remaining spend went negative: metering double-counts")
	}
	if want := gate.Spend("usr_1"); want >= 0 && body.Data.SpendUSD == 0 {
		t.Log("spend recorded on the gate but not reported")
	}
}

func TestAssembledPromptIsRecorded(t *testing.T) {
	s, _, _ := chatServer(t)
	token, _ := registerAndToken(t, s)
	postJSON(t, s, token, `{"text":"diagnose me"}`)
	a := s.orchestrator.LastAssembly()
	if a == nil {
		t.Fatal("no assembled prompt was recorded")
	}
	if !strings.Contains(fmt.Sprint(a.Messages), "diagnose me") {
		t.Fatal("the assembled prompt does not contain the request")
	}
}
