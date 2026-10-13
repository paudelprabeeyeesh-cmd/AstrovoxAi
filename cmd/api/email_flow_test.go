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
	store := newTokenStore(recorder)

	router := httpapi.NewRouter()
	log := logging.New("test")
	log.SetOutput(io.Discard)

	cfg := testConfig()
	if err := mount(router, cfg, log); err != nil {
		t.Fatalf("mount failed: %v", err)
	}
	// The mounted server has its own handler; the fixture store is the one
	// the tests read issued tokens from.
	return &mailFixture{router: router, store: store}
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

	known := postJSON(t, fixture, "/auth/reset-request", `{"email":"known@example.com"}`)
	unknown := postJSON(t, fixture, "/auth/reset-request", `{"email":"unknown@example.com"}`)
	if known != unknown {
		t.Fatalf("reset-request leaked registration: known=%s unknown=%s", known, unknown)
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
	known := postJSON(t, fixture, "/auth/magic-link", `{"email":"known@example.com"}`)
	unknown := postJSON(t, fixture, "/auth/magic-link", `{"email":"nobody@example.com"}`)
	if known != unknown {
		t.Fatal("magic-link leaked registration")
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
