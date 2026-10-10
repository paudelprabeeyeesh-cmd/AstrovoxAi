package auth

import (
	"errors"
	"testing"
	"time"
)

func errorsIs(err, target error) bool { return errors.Is(err, target) }

func newTestSigner() *JWTSigner {
	return NewJWTSigner("test-secret", "astrovox", time.Hour)
}

func TestJWTRoundTrip(t *testing.T) {
	s := newTestSigner()
	tok, err := s.Issue(&Claims{Subject: "user-1", Roles: []string{"admin"}})
	if err != nil {
		t.Fatal(err)
	}
	claims, err := s.Verify(tok)
	if err != nil {
		t.Fatal(err)
	}
	if claims.Subject != "user-1" || !claims.HasRole("admin") {
		t.Errorf("claims: %+v", claims)
	}
	if claims.Issuer != "astrovox" {
		t.Errorf("issuer: %s", claims.Issuer)
	}
	if claims.ExpiresAt <= time.Now().Unix() {
		t.Error("expected future expiry")
	}
	st := s.Stats()
	if st.Issued == 0 || st.Verified == 0 {
		t.Error("stats")
	}
}

func TestJWTBadSignature(t *testing.T) {
	s := newTestSigner()
	tok, _ := s.Issue(&Claims{Subject: "u"})
	// Tamper with the payload.
	bad := tok[:len(tok)-4] + "AAAA"
	if _, err := s.Verify(bad); err == nil {
		t.Error("expected signature error")
	}
}

func TestJWTStructured(t *testing.T) {
	s := newTestSigner()
	if _, err := s.Verify("not-a-token"); err == nil {
		t.Error("expected invalid token error")
	}
}

func TestJWTExpired(t *testing.T) {
	s := newTestSigner()
	if _, err := s.Issue(nil); err == nil {
		t.Error("expected nil claims error")
	}
	tok, err := s.Issue(&Claims{Subject: "u", ExpiresAt: time.Now().Add(-time.Hour).Unix()})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := s.Verify(tok); err != ErrTokenExpired {
		t.Errorf("expected expiry error, got %v", err)
	}
}

func TestJWTNotYetValid(t *testing.T) {
	s := newTestSigner()
	tok, _ := s.Issue(&Claims{Subject: "u", NotBefore: time.Now().Add(time.Hour).Unix(), ExpiresAt: time.Now().Add(2 * time.Hour).Unix()})
	if _, err := s.Verify(tok); err == nil {
		t.Error("expected not-yet-valid error")
	}
}

func TestClaimsScope(t *testing.T) {
	c := &Claims{Scope: "read write admin"}
	if !c.HasScope("read") || !c.HasScope("admin") {
		t.Error("scope parsing")
	}
	if c.HasScope("delete") {
		t.Error("unexpected scope")
	}
}

func TestOAuthClientCredentials(t *testing.T) {
	s := newTestSigner()
	srv := NewOAuthServer(s)
	if err := srv.RegisterClient(&OAuthClient{
		ID: "app", Secret: "shh", Scopes: []string{"read", "write"},
	}); err != nil {
		t.Fatal(err)
	}
	resp, err := srv.Token(&TokenRequest{
		GrantType: "client_credentials", ClientID: "app", ClientSecret: "shh", Scope: "read write",
	})
	if err != nil {
		t.Fatal(err)
	}
	if resp.TokenType != "Bearer" || resp.AccessToken == "" {
		t.Errorf("response: %+v", resp)
	}
	if resp.ExpiresIn <= 0 {
		t.Error("expected positive expiry")
	}
}

func TestOAuthBadGrant(t *testing.T) {
	srv := NewOAuthServer(newTestSigner())
	if _, err := srv.Token(&TokenRequest{GrantType: "password"}); err != ErrInvalidGrant {
		t.Error("expected invalid grant")
	}
	if _, err := srv.Token(nil); err != ErrInvalidGrant {
		t.Error("expected invalid grant for nil request")
	}
}

func TestOAuthUnknownClient(t *testing.T) {
	srv := NewOAuthServer(newTestSigner())
	if _, err := srv.Token(&TokenRequest{GrantType: "client_credentials", ClientID: "x", ClientSecret: "y"}); err != ErrUnknownClient {
		t.Errorf("expected unknown client, got %v", err)
	}
}

func TestOAuthScopeNotPermitted(t *testing.T) {
	srv := NewOAuthServer(newTestSigner())
	srv.RegisterClient(&OAuthClient{ID: "a", Secret: "s", Scopes: []string{"read"}})
	if _, err := srv.Token(&TokenRequest{GrantType: "client_credentials", ClientID: "a", ClientSecret: "s", Scope: "admin"}); err == nil {
		t.Error("expected scope rejection")
	}
}

func TestOAuthInvalidRegistration(t *testing.T) {
	srv := NewOAuthServer(newTestSigner())
	if srv.RegisterClient(nil) == nil {
		t.Error("expected error for nil client")
	}
}

func TestRoleStore(t *testing.T) {
	rs := NewRoleStore()
	rs.Assign("user", "admin")
	rs.Assign("user", "editor")
	if !rs.HasRole("user", "admin") || !rs.HasRole("user", "editor") {
		t.Error("role assignment")
	}
	rs.Revoke("user", "admin")
	if rs.HasRole("user", "admin") {
		t.Error("revoke failed")
	}
	if len(rs.Roles("nobody")) != 0 {
		t.Error("expected no roles")
	}
}

func TestRBACAuthorize(t *testing.T) {
	a := NewRBACAuthorizer(NewRoleStore())
	a.DefineRole(&Role{Name: "admin", Permissions: []string{"*:*"}})
	a.DefineRole(&Role{Name: "reader", Permissions: []string{"documents:read"}})

	// Assign via the authorizer's underlying store.
	store := a.store
	store.Assign("alice", "admin")
	store.Assign("bob", "reader")

	if !a.Authorize("alice", Permission{"documents", "write"}) {
		t.Error("admin should be allowed")
	}
	if !a.Authorize("bob", Permission{"documents", "read"}) {
		t.Error("reader should read")
	}
	if a.Authorize("bob", Permission{"documents", "write"}) {
		t.Error("reader must not write")
	}
}

func TestRBACCheck(t *testing.T) {
	a := NewRBACAuthorizer(NewRoleStore())
	a.DefineRole(&Role{Name: "r", Permissions: []string{"x:read"}})
	a.store.Assign("u", "r")
	if err := a.Check("u", Permission{"x", "read"}); err != nil {
		t.Fatal(err)
	}
	if err := a.Check("u", Permission{"x", "write"}); !errorsIs(err, ErrForbidden) {
		t.Errorf("expected forbidden, got %v", err)
	}
}

func TestRBACStats(t *testing.T) {
	a := NewRBACAuthorizer(NewRoleStore())
	a.DefineRole(&Role{Name: "r", Permissions: []string{"a:b"}})
	a.store.Assign("u", "r")
	a.Authorize("u", Permission{"a", "b"})
	a.Authorize("u", Permission{"z", "z"})
	st := a.Stats()
	if st.Allowed != 1 || st.Denied != 1 {
		t.Errorf("stats: %+v", st)
	}
}

func TestPermissionString(t *testing.T) {
	p := Permission{Resource: "model", Action: "infer"}
	if p.String() != "model:infer" {
		t.Errorf("got %s", p.String())
	}
}

func TestRBACWildcardRoles(t *testing.T) {
	a := NewRBACAuthorizer(NewRoleStore())
	a.DefineRole(&Role{Name: "w", Permissions: []string{"model:*"}})
	a.store.Assign("u", "w")
	if !a.Authorize("u", Permission{"model", "infer"}) {
		t.Error("wildcard resource should match")
	}
	if a.Authorize("u", Permission{"data", "read"}) {
		t.Error("wildcard must be scoped to the resource")
	}
}