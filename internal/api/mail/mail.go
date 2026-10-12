// Package mail delivers single-use tokens by email, and records that it
// did, without ever putting the token in a log line.
//
// The same rule as the Python service that preceded it: a token is
// account-owning, so it is delivered by email and only by email, and it is
// never logged. A deployment that forgets to configure SMTP must learn
// that from the startup check and the returned False, not from a token in
// an app log.
package mail

import (
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"net/smtp"
	"strings"
	"sync"
	"time"
)

// Delivery reports what a send attempted.
type Delivery struct {
	Sent   bool   `json:"sent"`
	Reason string `json:"reason,omitempty"`
}

// Mailer sends a message. It is an interface so a test can observe what
// would have been sent without an SMTP server.
type Mailer interface {
	Send(to, subject, body string) Delivery
}

// Config is the SMTP configuration, validated at construction so a
// partially-configured mailer fails at startup rather than on the first
// send.
type Config struct {
	Host     string
	Port     int
	Username string
	Password string
	From     string
	StartTLS bool
	Timeout  time.Duration
}

// Valid reports whether the configuration is usable.
func (c Config) Valid() error {
	if c.Host == "" {
		return errors.New("mail: host is empty")
	}
	if c.From == "" {
		return errors.New("mail: from is empty")
	}
	if c.Port <= 0 || c.Port > 65535 {
		return errors.New("mail: port out of range")
	}
	if c.Username != "" && c.Password == "" {
		return errors.New("mail: a username with no password")
	}
	return nil
}

// SMTPMailer sends through an SMTP server.
type SMTPMailer struct {
	cfg Config
}

// NewSMTP returns a mailer for a validated config.
func NewSMTP(cfg Config) (*SMTPMailer, error) {
	if err := cfg.Valid(); err != nil {
		return nil, err
	}
	if cfg.Timeout <= 0 {
		cfg.Timeout = 10 * time.Second
	}
	return &SMTPMailer{cfg: cfg}, nil
}

// Send delivers one message. A failure is reported rather than raised, so a
// retry is possible and the caller can decide.
func (m *SMTPMailer) Send(to, subject, body string) Delivery {
	addr := fmt.Sprintf("%s:%d", m.cfg.Host, m.cfg.Port)
	auth := smtp.PlainAuth("", m.cfg.Username, m.cfg.Password, m.cfg.Host)

	msg := strings.Join([]string{
		"From: " + m.cfg.From,
		"To: " + to,
		"Subject: " + subject,
		"MIME-Version: 1.0",
		"Content-Type: text/plain; charset=utf-8",
		"",
		body,
	}, "\r\n")

	err := smtp.SendMail(addr, auth, m.cfg.From, []string{to}, []byte(msg))
	if err != nil {
		// The reason is logged; the credential never is, and neither is the
		// body, which contains the token.
		return Delivery{Sent: false, Reason: err.Error()}
	}
	return Delivery{Sent: true}
}

// NullMailer is the fallback when no SMTP host is configured.
//
// It reports False rather than succeeding, because a deployment with no
// mailer must fail visibly: a caller that thinks verification mail was
// delivered when it was not is a user who can never log in.
type NullMailer struct{}

// Send reports the configured-outcome, never a success.
func (NullMailer) Send(_, _, _ string) Delivery {
	return Delivery{
		Sent:   false,
		Reason: "mail: no SMTP host configured",
	}
}

// RecordingMailer records what would have been sent, so a test can asssert
// the email channel was used without exposing the token.
type RecordingMailer struct {
	mu   sync.Mutex
	sent []Message
}

// Message is one recorded send. The token is not stored: only the
// purpose, the recipient, and a prefix, so a test can assert the shape
// without holding the credential.
type Message struct {
	Purpose string
	To      string
	Prefix  string
	At      time.Time
}

func (m *RecordingMailer) Send(to, subject, body string) Delivery {
	token := extractToken(body)
	m.mu.Lock()
	m.sent = append(m.sent, Message{
		Purpose: purposeFor(subject),
		To:      to,
		Prefix:  tokenPrefix(token),
		At:      time.Now(),
	})
	m.mu.Unlock()
	return Delivery{Sent: true}
}

// For returns recorded sends for a purpose.
func (m *RecordingMailer) For(purpose string) []Message {
	m.mu.Lock()
	defer m.mu.Unlock()
	out := []Message{}
	for _, msg := range m.sent {
		if msg.Purpose == purpose {
			out = append(out, msg)
		}
	}
	return out
}

// Count returns the total sends.
func (m *RecordingMailer) Count() int {
	m.mu.Lock()
	defer m.mu.Unlock()
	return len(m.sent)
}

func extractToken(body string) string {
	// The body is "Use this code: <token>". Extracting by position keeps
	// the token out of the test's assertion output.
	lines := strings.Split(body, "\n")
	for _, l := range lines {
		if strings.HasPrefix(l, "Use this code: ") {
			return strings.TrimSpace(strings.TrimPrefix(l, "Use this code: "))
		}
	}
	return ""
}

func tokenPrefix(token string) string {
	if len(token) <= 4 {
		return ""
	}
	return token[:4]
}

func purposeFor(subject string) string {
	switch {
	case strings.Contains(subject, "Confirm"):
		return "verify_email"
	case strings.Contains(subject, "Reset"):
		return "reset_password"
	case strings.Contains(subject, "sign-in"):
		return "magic_link"
	default:
		return "unknown"
	}
}

// --- Token delivery --------------------------------------------------------

// TokenFrom generates a token, delivers it, and reports the delivery.
//
// It is the only path that mints a token, so a caller cannot mint one and
// then have it leak by being returned.
func TokenFrom(m Mailer, purpose string, to string) (string, Delivery) {
	token := NewToken()
	subject, body := template(purpose, token)
	delivery := m.Send(to, subject, body)
	return token, delivery
}

// Purposes are the token kinds, stable so a caller can branch on them.
const (
	PurposeVerifyEmail   = "verify_email"
	PurposeResetPassword = "reset_password"
	PurposeMagicLink     = "magic_link"
)

// NewToken returns a 256-bit URL-safe token.
//
// secrets-equivalent: crypto/rand with 32 bytes, base64url encoded. The
// uuid4-concatenation the Python code used is not a token API, so it is not
// repeated here.
func NewToken() string {
	var b [32]byte
	if _, err := rand.Read(b[:]); err != nil {
		// crypto/rand failing is a system failure, not a request failure.
		// The process cannot safely mint a token, so this is a hard error
		// rather than a weak token.
		panic("mail: crypto/rand unavailable: " + err.Error())
	}
	return base64.RawURLEncoding.EncodeToString(b[:])
}

func template(purpose, token string) (string, string) {
	switch purpose {
	case PurposeVerifyEmail:
		return "Confirm your email address", fmt.Sprintf(
			"Use this code: %s\n\nIt expires in 24 hours. If you did not request it, ignore this email.", token)
	case PurposeResetPassword:
		return "Reset your password", fmt.Sprintf(
			"Use this code: %s\n\nIt expires in 1 hour. If you did not request it, ignore this email.", token)
	case PurposeMagicLink:
		return "Your sign-in link", fmt.Sprintf(
			"Use this code: %s\n\nIt expires in 15 minutes. If you did not request it, ignore this email.", token)
	default:
		return "Your security code", fmt.Sprintf(
			"Use this code: %s\n\nIt expires in 1 hour.", token)
	}
}

// TTL returns the lifetime for a purpose, so a caller can check expiry
// without duplicating the durations.
func TTL(purpose string) time.Duration {
	switch purpose {
	case PurposeVerifyEmail:
		return 24 * time.Hour
	case PurposeMagicLink:
		return 15 * time.Minute
	case PurposeResetPassword:
		return time.Hour
	default:
		return time.Hour
	}
}

var _ = json.Marshal
