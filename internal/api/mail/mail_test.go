package mail

import (
	"strings"
	"testing"
)

func TestNewTokenIsLongAndURLSafe(t *testing.T) {
	token := NewToken()
	// 32 bytes base64url-encoded is 43 characters. Shorter than 128 bits
	// is not a token that survives a credential-stuffing window.
	if len(token) < 40 {
		t.Fatalf("token length = %d, want at least 40", len(token))
	}
	for _, r := range token {
		if strings.ContainsRune("+/=", r) {
			t.Fatalf("token is not URL-safe: %q", token)
		}
	}
}

func TestNewTokenAreUnique(t *testing.T) {
	// Two identical tokens would make a verification bypass: the same code
	// accepted for two accounts.
	seen := map[string]bool{}
	for i := 20000; i > 0; i-- {
		token := NewToken()
		if seen[token] {
			t.Fatalf("duplicate token generated: %q", token)
		}
		seen[token] = true
	}
}

func TestTokenFromDeliversViaMail(t *testing.T) {
	rec := &RecordingMailer{}
	token, delivery := TokenFrom(rec, PurposeVerifyEmail, "user@example.com")

	if !delivery.Sent {
		t.Fatal("the token was not delivered")
	}
	if len(token) < 40 {
		t.Fatalf("token length = %d", len(token))
	}
	sent := rec.For(PurposeVerifyEmail)
	if len(sent) != 1 {
		t.Fatalf("%d sends for the purpose, want 1", len(sent))
	}
	if sent[0].To != "user@example.com" {
		t.Fatalf("delivered to %q", sent[0].To)
	}
	// The token must not be stored by the recorder: holding it is the leak
	// the recorder exists to prevent.
	for _, msg := range rec.sent {
		if msg.Prefix != "" && len(msg.Prefix) >= len(token) {
			t.Fatal("the recorder holds the whole token")
		}
	}
}

func TestRecordingMailerStoresNoToken(t *testing.T) {
	rec := &RecordingMailer{}
	token, _ := TokenFrom(rec, PurposeResetPassword, "user@example.com")

	for _, msg := range rec.sent {
		if msg.Prefix == token {
			t.Fatal("the recorder stored the full token")
		}
	}
	// The recorded prefix is a prefix, so a test can still assert the shape.
	if len(rec.sent) == 1 && rec.sent[0].Prefix != token[:4] {
		t.Fatalf("prefix = %q, want the token's first 4 chars", rec.sent[0].Prefix)
	}
}

func TestNullMailerFailsClosed(t *testing.T) {
	// A deployment with no mailer must fail visibly. A caller that thinks
	// verification mail was delivered when it was not is a user who can
	// never log in.
	d := NullMailer{}.Send("user@example.com", "Confirm your email address", "Use this code: x")
	if d.Sent {
		t.Fatal("the null mailer reported a success")
	}
	if d.Reason == "" {
		t.Fatal("no reason given for the failure")
	}
}

func TestConfigValidation(t *testing.T) {
	good := Config{Host: "smtp.example.com", Port: 587, From: "noreply@example.com"}
	if err := good.Valid(); err != nil {
		t.Fatalf("a valid config was rejected: %v", err)
	}

	cases := []Config{
		{Host: "", Port: 587, From: "x@y.z"},
		{Host: "smtp.example.com", Port: 587, From: ""},
		{Host: "smtp.example.com", Port: 0, From: "x@y.z"},
		{Host: "smtp.example.com", Port: 70000, From: "x@y.z"},
		{Host: "smtp.example.com", Port: 587, From: "x@y.z", Username: "u"},
	}
	for i, cfg := range cases {
		if cfg.Valid() == nil {
			t.Errorf("case %d: an invalid config was accepted", i)
		}
	}
}

func TestNewSMTPRefusesAnInvalidConfig(t *testing.T) {
	if _, err := NewSMTP(Config{Host: "", Port: 587, From: "x@y.z"}); err == nil {
		t.Fatal("an invalid config built a mailer")
	}
	if _, err := NewSMTP(Config{Host: "h", Port: 587, From: "x@y.z"}); err != nil {
		t.Fatalf("a valid config was refused: %v", err)
	}
}

func TestNewSMTPDefaultsTheTimeout(t *testing.T) {
	// A zero timeout would hang the send forever rather than defaulting to
	// hang, which is how a timeout would silently default to zero and hang.
	m, err := NewSMTP(Config{Host: "smtp.example.com", Port: 587, From: "x@y.z"})
	if err != nil {
		t.Fatalf("NewSMTP failed: %v", err)
	}
	if m.cfg.Timeout <= 0 {
		t.Fatal("the timeout was left at zero")
	}
}

func TestTTLCoversEveryPurpose(t *testing.T) {
	// A caller checks expiry against TTL, so a purpose with none would be
	// accepted forever.
	for _, purpose := range []string{
		PurposeVerifyEmail, PurposeResetPassword, PurposeMagicLink,
	} {
		if TTL(purpose) <= 0 {
			t.Fatalf("purpose %q has no TTL", purpose)
		}
	}
	if TTL("unknown-purpose") <= 0 {
		t.Fatal("the default TTL is zero")
	}
	if TTL(PurposeMagicLink) >= TTL(PurposeVerifyEmail) {
		t.Fatal("a magic link lives as long as a verification token")
	}
}

func TestTemplateIncludesTheTokenAndAnExpiry(t *testing.T) {
	subject, body := template(PurposeVerifyEmail, "TOKEN-VALUE")
	if !strings.Contains(subject, "Confirm") {
		t.Fatalf("subject = %q", subject)
	}
	if !strings.Contains(body, "TOKEN-VALUE") {
		t.Fatal("the token is not in the body")
	}
	if !strings.Contains(body, "expires") {
		t.Fatal("the body does not state an expiry")
	}
}

func TestTemplateCoversEveryPurpose(t *testing.T) {
	// A purpose with no branch would send a generic code, which a caller
	// cannot tell apart from a real verification email.
	for _, purpose := range []string{
		PurposeVerifyEmail, PurposeResetPassword, PurposeMagicLink,
	} {
		subject, body := template(purpose, "T")
		if subject == "" || body == "" {
			t.Fatalf("purpose %q produced an empty template", purpose)
		}
		if !strings.Contains(body, "T") {
			t.Fatalf("purpose %q did not include the token", purpose)
		}
	}
}

func TestExtractTokenParsesTheBody(t *testing.T) {
	body := "Use this code: abc123\n\nIt expires in 1 hour."
	if got := extractToken(body); got != "abc123" {
		t.Fatalf("extractToken = %q", got)
	}
	if got := extractToken("no token here"); got != "" {
		t.Fatalf("extractToken = %q, want empty", got)
	}
}

func TestTokenPrefixIsBounded(t *testing.T) {
	// The prefix exists so a test can assert the shape, so it must be
	// bounded: a full-length prefix would leak the token.
	token := "0123456789abcdef"
	if got := tokenPrefix(token); len(got) > 4 {
		t.Fatalf("prefix = %q, want at most 4 chars", got)
	}
	if got := tokenPrefix("abc"); got != "" {
		t.Fatalf("prefix = %q, want empty for a short token", got)
	}
}
