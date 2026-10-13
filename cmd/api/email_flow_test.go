package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/astrovox/astrovox/internal/api/logging"
	"github.com/astrovox/astrovox/internal/api/mail"
	"github.com/astrovox/astrovox/internal/httpapi"
)

// mailFixture is a server whose mailer records what would have been sent,
// so a test can assert the email channel was used without holding the
// token in an assertion message.
type mailFixture struct {
	router *httpapi.Router
	store  *tokenStore
}

func newMailFixture(t *testing.T) *mailFixture {
	t.Helper()
	recorder := &mail.RecordingMailer{}

	router := httpapi.NewRouter()
	log := logging.New("test")
	log.SetOutput(io.Discard)

	cfg := testConfig()
	// mount() builds a tokenStore around defaultMailer(), which in a test
	// environment is the null mailer. Install the recorder first so the
	// store the endpoints use wraps the recorder; the fixture reads its own
	// store, which is the one that issued the tokens the test redeems.
	setTestMailer(recorder)
	// The auth handlers share one process-wide store, so the fixture reads
	// that store rather than building a second one.
	resetAuthStoreForTest()
	if err := mount(router, cfg, log); err != nil {
		t.Fatalf("mount failed: %v", err)
	}
	return &mailFixture{router: router, store: authTokenStore()}
}

func doJSON(t *testing.T, fixture *mailFixture, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	rec := httptest.NewRecorder()
	fixture.router.ServeHTTP(rec, req)
	return rec
}

func postJSON(t *testing.T, fixture *mailFixture, path, body string) string {
	t.Helper()
	return doJSON(t, fixture, "POST", path, body).Body.String()
}

func registerAccount(t *testing.T, fixture *mailFixture, email string) {
	t.Helper()
	body, _ := json.Marshal(map[string]string{
		"email":    email,
		"password": "password123",
	})
	rec := doJSON(t, fixture, "POST", "/auth/register", string(body))
	if rec.Code != http.StatusCreated {
		t.Fatalf("register = %d, want 201: %s", rec.Code, rec.Body.String())
	}
}

// issueForPurpose issues a token through the endpoint and reads it back from
// the store. The store is the only place the whole token still exists, so a
// test can redeem it without holding it in an assertion message.
func issueForPurpose(t *testing.T, fixture *mailFixture, email, purpose string) string {
	t.Helper()
	postJSON(t, fixture, "/auth/reset-request", `{"email":"`+email+`"}`)
	// Force the store's own clock: the endpoints above issued a reset token,
	// so reuse it directly for the requested purpose.
	if purpose == mail.PurposeResetPassword {
		for token, rec := range fixture.store.tokens {
			if rec.purpose == mail.PurposeResetPassword && !rec.used {
				return token
			}
		}
	}
	// For the other purposes, ask the store directly with the recorded
	// mailer so the token is issued through the same delivery path.
	token, err := fixture.store.issue(email, purpose)
	if err != nil {
		t.Fatalf("issue failed: %v", err)
	}
	return token
}

func TestResetRequestDoesNotRevealRegistration(t *testing.T) {
	// The reply must be identical whether or not the address exists, or the
	// endpoint is a user-enumeration oracle.
	fixture := newMailFixture(t)
	registerAccount(t, fixture, "known@example.com")

	known := doJSON(t, fixture, "POST", "/auth/reset-request", `{"email":"known@example.com"}`)
	unknown := doJSON(t, fixture, "POST", "/auth/reset-request", `{"email":"unknown@example.com"}`)
	if known.Code != unknown.Code {
		t.Fatalf("reset-request leaked registration by status: known=%d unknown=%d", known.Code, unknown.Code)
	}
	// Compare the message, not the request id, which is per-call and random.
	knownMsg := jsonField(t, known.Body.Bytes(), "data", "message")
	unknownMsg := jsonField(t, unknown.Body.Bytes(), "data", "message")
	if knownMsg != unknownMsg {
		t.Fatalf("reset-request leaked registration by message: known=%q unknown=%q", knownMsg, unknownMsg)
	}
}

func TestResetRequestDoesNotReturnTheToken(t *testing.T) {
	// The token is account-owning, so it must be email-only. A response
	// that carries one is an account-takeover primitive.
	fixture := newMailFixture(t)
	registerAccount(t, fixture, "reset@example.com")

	body := postJSON(t, fixture, "/auth/reset-request", `{"email":"reset@example.com"}`)
	for _, forbidden := range []string{"token", "reset_password", "magic_link"} {
		if strings.Contains(body, forbidden) {
			t.Fatalf("reset-request response carries %q", forbidden)
		}
	}
}

func TestResetPasswordUpdatesAndConsumes(t *testing.T) {
	fixture := newMailFixture(t)
	registerAccount(t, fixture, "changepw@example.com")
	issued := issueForPurpose(t, fixture, "changepw@example.com", mail.PurposeResetPassword)

	rec := doJSON(t, fixture, "POST", "/auth/reset",
		`{"token":"`+issued+`","password":"newpassword123"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("reset = %d, want 200: %s", rec.Code, rec.Body.String())
	}

	// The token must be consumed, so it cannot be replayed.
	rec = doJSON(t, fixture, "POST", "/auth/reset",
		`{"token":"`+issued+`","password":"another12345"}`)
	if rec.Code == http.StatusOK {
		t.Fatal("a reset token was replayed")
	}
}

func TestMagicLinkDoesNotConfirmRegistration(t *testing.T) {
	fixture := newMailFixture(t)
	known := doJSON(t, fixture, "POST", "/auth/magic-link", `{"email":"known@example.com"}`)
	unknown := doJSON(t, fixture, "POST", "/auth/magic-link", `{"email":"nobody@example.com"}`)
	if known.Code != unknown.Code {
		t.Fatalf("magic-link leaked registration by status: known=%d unknown=%d", known.Code, unknown.Code)
	}
	knownMsg := jsonField(t, known.Body.Bytes(), "data", "message")
	unknownMsg := jsonField(t, unknown.Body.Bytes(), "data", "message")
	if knownMsg != unknownMsg {
		t.Fatalf("magic-link leaked registration by message: known=%q unknown=%q", knownMsg, unknownMsg)
	}
}

func TestMagicLinkDoesNotReturnTheToken(t *testing.T) {
	fixture := newMailFixture(t)
	registerAccount(t, fixture, "magic@example.com")
	body := postJSON(t, fixture, "/auth/magic-link", `{"email":"magic@example.com"}`)
	for _, forbidden := range []string{"token", "magic_link"} {
		if strings.Contains(body, forbidden) {
			t.Fatalf("magic-link response carries %q", forbidden)
		}
	}
}

func TestTokenIsSingleUse(t *testing.T) {
	// A single-use token is what makes an intercepted email a one-time
	// problem rather than a standing one.
	fixture := newMailFixture(t)
	registerAccount(t, fixture, "single@example.com")
	token, err := fixture.store.issue("single@example.com", mail.PurposeResetPassword)
	if err != nil {
		t.Fatalf("issue failed: %v", err)
	}

	email, ok := fixture.store.redeem(token, mail.PurposeResetPassword)
	if !ok || email != "single@example.com" {
		t.Fatalf("first redeem failed: ok=%v email=%q", ok, email)
	}
	if _, ok := fixture.store.redeem(token, mail.PurposeResetPassword); ok {
		t.Fatal("a token was redeemed twice")
	}
}

func TestTokenCannotBeRedeemedForAnotherPurpose(t *testing.T) {
	// A reset token must not open a sign-in session, or one leaked email
	// becomes a full account takeover.
	fixture := newMailFixture(t)
	token, err := fixture.store.issue("x@example.com", mail.PurposeResetPassword)
	if err != nil {
		t.Fatalf("issue failed: %v", err)
	}
	if _, ok := fixture.store.redeem(token, mail.PurposeMagicLink); ok {
		t.Fatal("a reset token was redeemed as a magic link")
	}
}

func TestTokenExpires(t *testing.T) {
	// An expired token must stop working, or a leaked email is permanent.
	store := newTokenStore(&mail.RecordingMailer{})
	token, err := store.issue("x@example.com", mail.PurposeResetPassword)
	if err != nil {
		t.Fatalf("issue failed: %v", err)
	}
	// Rewrite the expiry into the past.
	store.mu.Lock()
	store.tokens[token].expires = time.Now().Add(-time.Minute)
	store.mu.Unlock()

	if _, ok := store.redeem(token, mail.PurposeResetPassword); ok {
		t.Fatal("an expired token was redeemed")
	}
}

func TestPurgeRemovesExpired(t *testing.T) {
	// The token map must not grow without limit.
	store := newTokenStore(&mail.RecordingMailer{})
	for i := 0; i < 5; i++ {
		_, _ = store.issue(fmt.Sprintf("u%d@example.com", i), mail.PurposeResetPassword)
	}
	// Expire them all.
	store.mu.Lock()
	for _, rec := range store.tokens {
		rec.expires = time.Now().Add(-time.Second)
	}
	store.mu.Unlock()

	removed := store.purge()
	if removed != 5 {
		t.Fatalf("purged %d records, want 5", removed)
	}
	if len(store.tokens) != 0 {
		t.Fatal("expired records remain after purge")
	}
}

// jsonField reads a nested string field, so a test compares what a caller
// can observe rather than a per-call request id.
func jsonField(t *testing.T, body []byte, keys ...string) string {
	t.Helper()
	var decoded map[string]interface{}
	if err := json.Unmarshal(body, &decoded); err != nil {
		t.Fatalf("response is not JSON: %v", err)
	}
	var cur interface{} = decoded
	for _, k := range keys {
		m, ok := cur.(map[string]interface{})
		if !ok {
			t.Fatalf("field path %v not present in %s", keys, body)
		}
		cur = m[k]
	}
	if s, ok := cur.(string); ok {
		return s
	}
	return ""
}

// Test mailer hooks. The default mailer reads the environment, which in a
// test is empty; these let a fixture install a recorder for the duration
// of one test without touching the environment.
var testMailerOverride *mail.RecordingMailer

func setTestMailer(m *mail.RecordingMailer) {
	testMailerOverride = m
	authStoreMailerOverride = m
}

func clearTestMailer() {
	testMailerOverride = nil
	authStoreMailerOverride = nil
}

// resetAuthStoreForTest drops the process-wide auth store so a fresh
// fixture builds one around the recorder it just installed. Without this,
// the first test's store (wrapping the null mailer) is reused and every
// later issuance fails the same way.
func resetAuthStoreForTest() {
	authStore = nil
}
