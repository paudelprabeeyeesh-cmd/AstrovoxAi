package main

import (
	"sync"
	"time"

	"github.com/astrovox/astrovox/internal/api/mail"
)

// tokenStore issues and redeems single-use email tokens.
//
// The store is in-process, so a restart invalidates every outstanding
// token. That is the honest behaviour for a reference implementation: a
// durable store is a schema decision, and pretending otherwise would mean
// a token that survives a database wipe.
type tokenStore struct {
	mu     sync.Mutex
	tokens map[string]*tokenRecord
	mailer mail.Mailer
}

type tokenRecord struct {
	email   string
	purpose string
	expires time.Time
	used    bool
}

// newTokenStore returns a store that delivers whatever it issues.
func newTokenStore(m mail.Mailer) *tokenStore {
	return &tokenStore{tokens: map[string]*tokenRecord{}, mailer: m}
}

// issue mints a token, delivers it by email, and records it.
//
// The token is returned to the caller only so it can be used in a test. An
// endpoint that returns it to a user is the leak this module exists to
// prevent, so the returned value is deliberately discarded by the handlers.
func (s *tokenStore) issue(email, purpose string) (string, error) {
	token, delivery := mail.TokenFrom(s.mailer, purpose, email)
	if !delivery.Sent {
		return "", errMailUnavailable(delivery.Reason)
	}
	s.mu.Lock()
	s.tokens[token] = &tokenRecord{
		email:   email,
		purpose: purpose,
		expires: time.Now().Add(mail.TTL(purpose)),
	}
	s.mu.Unlock()
	return token, nil
}

// redeem validates and consumes a token.
//
// A token is single use, so a second redemption fails even inside the
// window. Token reuse is what makes a leaked email link permanent, so the
// consumed flag is set before the result is returned rather than after.
func (s *tokenStore) redeem(token, purpose string) (string, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	rec, ok := s.tokens[token]
	if !ok {
		return "", false
	}
	if rec.used || time.Now().After(rec.expires) {
		return "", false
	}
	if rec.purpose != purpose {
		return "", false
	}
	rec.used = true
	return rec.email, true
}

// purge drops expired records, so the map cannot grow without limit.
func (s *tokenStore) purge() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	before := len(s.tokens)
	for k, v := range s.tokens {
		if time.Now().After(v.expires) {
			delete(s.tokens, k)
		}
	}
	return before - len(s.tokens)
}

// errMailUnavailable marks a delivery failure, so a caller can tell
// "the mailer is not configured" from "the token was refused".
func errMailUnavailable(reason string) error {
	return &mailError{reason: reason}
}

type mailError struct{ reason string }

func (e *mailError) Error() string {
	return "token delivery unavailable: " + e.reason
}
