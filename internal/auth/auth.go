// Package auth provides JWT issue/verify, OAuth 2.0 client credentials
// flow, and role-based access control (RBAC).
package auth

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"sync"
	"time"
)

// Auth errors.
var (
	ErrInvalidToken  = errors.New("invalid token")
	ErrTokenExpired  = errors.New("token expired")
	ErrBadSignature  = errors.New("bad signature")
	ErrForbidden     = errors.New("forbidden")
	ErrUnknownClient = errors.New("unknown oauth client")
	ErrInvalidGrant  = errors.New("invalid grant")
)

// Header is a JWT header.
type Header struct {
	Alg string `json:"alg"`
	Typ string `json:"typ"`
}

// Claims are JWT registered + custom claims.
type Claims struct {
	Issuer    string                 `json:"iss,omitempty"`
	Subject   string                 `json:"sub,omitempty"`
	Audience  string                 `json:"aud,omitempty"`
	ExpiresAt int64                  `json:"exp,omitempty"`
	NotBefore int64                  `json:"nbf,omitempty"`
	IssuedAt  int64                  `json:"iat,omitempty"`
	ID        string                 `json:"jti,omitempty"`
	Roles     []string               `json:"roles,omitempty"`
	Scope     string                 `json:"scope,omitempty"`
	Custom    map[string]interface{} `json:"custom,omitempty"`
}

// Valid reports whether the claims are currently valid.
func (c *Claims) Valid(now time.Time) error {
	u := now.Unix()
	if c.ExpiresAt > 0 && u > c.ExpiresAt {
		return ErrTokenExpired
	}
	if c.NotBefore > 0 && u < c.NotBefore {
		return errors.New("token not yet valid")
	}
	return nil
}

// HasRole reports whether a claim carries a role.
func (c *Claims) HasRole(role string) bool {
	for _, r := range c.Roles {
		if r == role {
			return true
		}
	}
	return false
}

// HasScope reports whether a claim carries a scope token.
func (c *Claims) HasScope(scope string) bool {
	for _, s := range strings.Fields(c.Scope) {
		if s == scope {
			return true
		}
	}
	return false
}

// JWTSigner issues and verifies HMAC-SHA256 tokens.
type JWTSigner struct {
	secret []byte
	issuer string
	ttl    time.Duration
	mu     sync.RWMutex
	nextID uint64
	stats  JWTStats
}

// JWTStats tracks token statistics.
type JWTStats struct {
	Issued   uint64
	Verified uint64
	Rejected uint64
}

// NewJWTSigner creates a signer with an HMAC secret.
func NewJWTSigner(secret string, issuer string, ttl time.Duration) *JWTSigner {
	return &JWTSigner{secret: []byte(secret), issuer: issuer, ttl: ttl}
}

// Issue creates and signs a token.
func (s *JWTSigner) Issue(claims *Claims) (string, error) {
	if claims == nil {
		return "", errors.New("nil claims")
	}
	now := time.Now()
	if claims.IssuedAt == 0 {
		claims.IssuedAt = now.Unix()
	}
	if claims.ExpiresAt == 0 && s.ttl > 0 {
		claims.ExpiresAt = now.Add(s.ttl).Unix()
	}
	if claims.Issuer == "" {
		claims.Issuer = s.issuer
	}
	h := Header{Alg: "HS256", Typ: "JWT"}

	headerJSON, err := json.Marshal(h)
	if err != nil {
		return "", err
	}
	claimsJSON, err := json.Marshal(claims)
	if err != nil {
		return "", err
	}

	signingInput := b64(headerJSON) + "." + b64(claimsJSON)
	sig := s.sign(signingInput)
	s.mu.Lock()
	s.stats.Issued++
	s.mu.Unlock()
	return signingInput + "." + sig, nil
}

// Verify parses and validates a token, returning its claims.
func (s *JWTSigner) Verify(token string) (*Claims, error) {
	parts := strings.Split(token, ".")
	if len(parts) != 3 {
		return nil, ErrInvalidToken
	}
	signingInput := parts[0] + "." + parts[1]
	want := s.sign(signingInput)
	if !hmac.Equal([]byte(want), []byte(parts[2])) {
		s.mu.Lock()
		s.stats.Rejected++
		s.mu.Unlock()
		return nil, ErrBadSignature
	}
	claimsJSON, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return nil, ErrInvalidToken
	}
	var c Claims
	if err := json.Unmarshal(claimsJSON, &c); err != nil {
		return nil, ErrInvalidToken
	}
	if err := c.Valid(time.Now()); err != nil {
		s.mu.Lock()
		s.stats.Rejected++
		s.mu.Unlock()
		return nil, err
	}
	s.mu.Lock()
	s.stats.Verified++
	s.mu.Unlock()
	return &c, nil
}

func (s *JWTSigner) sign(input string) string {
	m := hmac.New(sha256.New, s.secret)
	m.Write([]byte(input))
	return b64(m.Sum(nil))
}

func b64(b []byte) string {
	return base64.RawURLEncoding.EncodeToString(b)
}

// Stats returns JWT statistics.
func (s *JWTSigner) Stats() JWTStats {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.stats
}

// TokenRequest is an OAuth 2.0 token request (client_credentials grant).
type TokenRequest struct {
	GrantType    string `json:"grant_type"`
	ClientID     string `json:"client_id"`
	ClientSecret string `json:"client_secret"`
	Scope        string `json:"scope"`
}

// TokenResponse is an OAuth 2.0 token response.
type TokenResponse struct {
	AccessToken string `json:"access_token"`
	TokenType   string `json:"token_type"`
	ExpiresIn   int64  `json:"expires_in"`
	Scope       string `json:"scope,omitempty"`
}

// OAuthClient is a registered OAuth client.
type OAuthClient struct {
	ID          string
	Secret      string
	Scopes      []string
	GrantTypes  []string
	RedirectURI string
}

// OAuthServer implements the client-credentials grant.
type OAuthServer struct {
	signer  *JWTSigner
	mu      sync.RWMutex
	clients map[string]*OAuthClient
}

// NewOAuthServer creates an OAuth server backed by a JWT signer.
func NewOAuthServer(signer *JWTSigner) *OAuthServer {
	return &OAuthServer{signer: signer, clients: make(map[string]*OAuthClient)}
}

// RegisterClient registers a client application.
func (s *OAuthServer) RegisterClient(c *OAuthClient) error {
	if c == nil || c.ID == "" {
		return errors.New("invalid client")
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	s.clients[c.ID] = c
	return nil
}

// Token issues a token for a valid client-credentials request.
func (s *OAuthServer) Token(req *TokenRequest) (*TokenResponse, error) {
	if req == nil || req.GrantType != "client_credentials" {
		return nil, ErrInvalidGrant
	}
	s.mu.RLock()
	c, ok := s.clients[req.ClientID]
	s.mu.RUnlock()
	if !ok || c.Secret != req.ClientSecret {
		return nil, ErrUnknownClient
	}
	if req.Scope != "" && !clientAllowsScope(c, req.Scope) {
		return nil, fmt.Errorf("%w: scope %q not permitted", ErrInvalidGrant, req.Scope)
	}

	claims := &Claims{
		Subject: c.ID,
		Scope:   req.Scope,
	}
	tok, err := s.signer.Issue(claims)
	if err != nil {
		return nil, err
	}
	var exp int64
	if verified, err := s.signer.Verify(tok); err == nil {
		exp = verified.ExpiresAt - time.Now().Unix()
	}
	return &TokenResponse{
		AccessToken: tok,
		TokenType:   "Bearer",
		ExpiresIn:   exp,
		Scope:       req.Scope,
	}, nil
}

func clientAllowsScope(c *OAuthClient, scope string) bool {
	allowed := make(map[string]bool, len(c.Scopes))
	for _, s := range c.Scopes {
		allowed[s] = true
	}
	for _, want := range strings.Fields(scope) {
		if !allowed[want] {
			return false
		}
	}
	return true
}

// Role is a named set of permissions.
type Role struct {
	Name        string
	Permissions []string
}

// Permission is a resource:action pair.
type Permission struct {
	Resource string
	Action   string
}

// String renders "resource:action".
func (p Permission) String() string { return p.Resource + ":" + p.Action }

// RoleStore maps subjects to roles.
type RoleStore struct {
	mu    sync.RWMutex
	roles map[string][]string
}

// NewRoleStore creates a role store.
func NewRoleStore() *RoleStore {
	return &RoleStore{roles: make(map[string][]string)}
}

// Assign grants a role to a subject.
func (r *RoleStore) Assign(subject, role string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.roles[subject] = append(r.roles[subject], role)
}

// Revoke removes a role from a subject.
func (r *RoleStore) Revoke(subject, role string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	list := r.roles[subject]
	out := list[:0]
	for _, x := range list {
		if x != role {
			out = append(out, x)
		}
	}
	r.roles[subject] = out
}

// Roles returns a subject's roles.
func (r *RoleStore) Roles(subject string) []string {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return append([]string(nil), r.roles[subject]...)
}

// HasRole reports whether a subject carries a role.
func (r *RoleStore) HasRole(subject, role string) bool {
	for _, x := range r.Roles(subject) {
		if x == role {
			return true
		}
	}
	return false
}

// RBACAuthorizer answers "may subject do action on resource?".
type RBACAuthorizer struct {
	mu    sync.RWMutex
	roles map[string]*Role
	store *RoleStore
	stats RBACStats
}

// RBACStats tracks authorization statistics.
type RBACStats struct {
	Allowed uint64
	Denied  uint64
}

// NewRBACAuthorizer creates an authorizer.
func NewRBACAuthorizer(store *RoleStore) *RBACAuthorizer {
	if store == nil {
		store = NewRoleStore()
	}
	return &RBACAuthorizer{roles: make(map[string]*Role), store: store}
}

// DefineRole registers a role and its permissions.
func (a *RBACAuthorizer) DefineRole(r *Role) {
	if r == nil || r.Name == "" {
		return
	}
	a.mu.Lock()
	a.roles[r.Name] = r
	a.mu.Unlock()
}

// RolesOf returns the roles assigned to a subject.
func (a *RBACAuthorizer) RolesOf(subject string) []string {
	return a.store.Roles(subject)
}

// Authorize checks a permission across the subject's roles.
func (a *RBACAuthorizer) Authorize(subject string, p Permission) bool {
	a.mu.RLock()
	granted := false
	for _, rn := range a.store.Roles(subject) {
		role, ok := a.roles[rn]
		if !ok {
			continue
		}
		for _, perm := range role.Permissions {
			if perm == p.String() || perm == "*"+p.Action || perm == p.Resource+":*" || perm == "*:*" {
				granted = true
				break
			}
		}
		if granted {
			break
		}
	}
	a.mu.RUnlock()

	a.mu.Lock()
	if granted {
		a.stats.Allowed++
	} else {
		a.stats.Denied++
	}
	a.mu.Unlock()
	return granted
}

// Check authorizes and returns ErrForbidden when denied.
func (a *RBACAuthorizer) Check(subject string, p Permission) error {
	if !a.Authorize(subject, p) {
		return fmt.Errorf("%w: %s cannot %s", ErrForbidden, subject, p)
	}
	return nil
}

// Stats returns authorization statistics.
func (a *RBACAuthorizer) Stats() RBACStats {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.stats
}
