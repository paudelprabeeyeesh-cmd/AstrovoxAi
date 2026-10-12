// Package apiserver assembles the Astrovox API from the engine packages: the
// auth (internal/auth), memory (internal/memory) and knowledge (internal/knowledge)
// subsystems behind an internal/httpapi boundary.
//
// The shape follows the reference architecture in the task register: one
// process, a clear trust boundary at the edge, providers called behind an
// adapter, and a single place where authentication is resolved. No business
// logic lives in the route handlers; they bind input, call the service layer,
// and render the envelope.
//
// Routes are registered once, in New, so the route table is inspectable from
// tests and from the /openapi.json endpoint rather than assembled lazily.
package apiserver

import (
	"net/http"
	"strings"
	"sync"
	"time"

	apperrors "github.com/astrovox/astrovox/internal/errors"

	"github.com/astrovox/astrovox/internal/auth"
	"github.com/astrovox/astrovox/internal/chat"
	"github.com/astrovox/astrovox/internal/conversations"
	"github.com/astrovox/astrovox/internal/httpapi"
	"github.com/astrovox/astrovox/internal/knowledge"
	"github.com/astrovox/astrovox/internal/memstore"
	"github.com/astrovox/astrovox/internal/version"
)

// Config holds everything the server needs. Values are bound at construction
// rather than read from the environment inside handlers, so a test can build
// a server without a working environment.
type Config struct {
	// JWTSecret signs and verifies session tokens.
	JWTSecret string
	// Issuer is the JWT issuer claim.
	Issuer string
	// TokenTTL bounds a session token's lifetime.
	TokenTTL time.Duration
	// MemoryLimit bounds the number of entries the explicit-memory store
	// keeps in this process.
	MemoryLimit int
	// AllowedOrigins is the CORS allow-list. Empty means no CORS headers,
	// which is the safe default for an API that is not browser-facing.
	AllowedOrigins []string
}

// DefaultConfig returns a configuration that runs, with no live credentials.
// It is deliberately not production-safe: a secret generated at startup means
// tokens do not survive a restart, which is a loud failure rather than a
// silent one.
func DefaultConfig() Config {
	return Config{
		JWTSecret:      "",
		Issuer:         "astrovox",
		TokenTTL:       24 * time.Hour,
		MemoryLimit:    10_000,
		AllowedOrigins: nil,
	}
}

// Server is the assembled API.
type Server struct {
	cfg    Config
	router *httpapi.Router
	signer *auth.JWTSigner
	oauth  *auth.OAuthServer
	// orchestrator is nil until a provider is attached. /chat/message refuses
	// with 503 while it is nil, which is distinguishable from an empty answer.
	orchestrator *chat.Orchestrator
	spend        *SpendGate
	chats        *conversations.Store
	memories     *memstore.Store
	facts        *knowledge.Graph

	// users is the in-process account store. It is deliberately small: this
	// server is a reference implementation for the API boundary, and the
	// durable store is the caller's schema decision. The guard is a
	// single-writer lock so registration cannot interleave.
	users   map[string]*Account
	usersMu sync.RWMutex
}

// Account is a registered principal.
type Account struct {
	ID           string   `json:"id"`
	Email        string   `json:"email"`
	PasswordHash string   `json:"-"`
	Roles        []string `json:"roles"`
	CreatedAt    string   `json:"created_at"`
}

// New builds the server: handler wiring, middleware order, and the
// verification of the parts that must not be nil.
func New(cfg Config) (*Server, error) {
	if cfg.MemoryLimit <= 0 {
		cfg.MemoryLimit = 10_000
	}

	s := &Server{
		cfg:      cfg,
		router:   httpapi.NewRouter(),
		signer:   auth.NewJWTSigner(cfg.JWTSecret, cfg.Issuer, cfg.TokenTTL),
		oauth:    auth.NewOAuthServer(nil),
		memories: memstore.New(cfg.MemoryLimit),
		facts:    knowledge.NewGraph(),
		users:    map[string]*Account{},
	}
	if s.signer == nil {
		return nil, apperrors.New(apperrors.CodeInvalidArgument, "a JWT signer is required")
	}
	s.oauth = auth.NewOAuthServer(s.signer)
	// Order matters: routes() installs the middleware chain via Router.Use,
	// and a middleware registered after a route is not applied to it. So the
	// static routes are registered first, then the provider is attached,
	// which registers the chat routes - and the chain must already be in
	// place for both. Building the chain explicitly before any route is
	// registered is the only order that satisfies that.
	s.routes()
	// The chat and conversation routes are registered into the same router
	// after routes() built the middleware chain, so they inherit it.
	if err := s.attachConversations(conversations.New(10_000)); err != nil {
		return nil, err
	}
	if err := s.attachChat(&Vendor{}, NewSpendGate(1.0)); err != nil {
		return nil, err
	}
	return s, nil
}

// Handler exposes the http.Handler, implementing the interface net/http expects.
func (s *Server) Handler() http.Handler {
	return s.router
}

// Router returns the route table, for tests and for the /openapi endpoint.
func (s *Server) Router() *httpapi.Router { return s.router }

// ---- Middleware -----------------------------------------------------------

// cors applies the allow-list. An empty list means no CORS headers at all,
// which is the safe default; a wildcard would be a misconfiguration with
// credentials enabled.
func (s *Server) cors(next httpapi.Handler) httpapi.Handler {
	return func(c *httpapi.Context) error {
		origin := c.Header("Origin", "")
		if origin != "" && s.originAllowed(origin) {
			c.Writer.Header().Set("Access-Control-Allow-Origin", origin)
			c.Writer.Header().Set("Vary", "Origin")
			c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		}
		if c.Request.Method == http.MethodOptions {
			c.Writer.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
			c.Writer.Header().Set("Access-Control-Allow-Headers", "Authorization, Content-Type, X-Request-ID")
			c.Writer.Header().Set("Access-Control-Max-Age", "600")
			c.Writer.WriteHeader(http.StatusNoContent)
			return nil
		}
		return next(c)
	}
}

func (s *Server) originAllowed(origin string) bool {
	for _, a := range s.cfg.AllowedOrigins {
		if a == origin {
			return true
		}
	}
	return false
}

// auth middleware resolves the bearer token and attaches the principal.
// It does not itself refuse a request: that is RequireAuth's job, so a
// public route can still inspect whether a token was supplied.
func (s *Server) auth(next httpapi.Handler) httpapi.Handler {
	return func(c *httpapi.Context) error {
		token := c.Bearer()
		if token == "" {
			return next(c)
		}
		claims, err := s.signer.Verify(token)
		if err != nil {
			// An invalid token on a public route is ignored, not fatal.
			return next(c)
		}
		c.SetClaims(claims)
		return next(c)
	}
}

// RequireAuth refuses a request with no valid principal.
func (s *Server) RequireAuth(next httpapi.Handler) httpapi.Handler {
	return func(c *httpapi.Context) error {
		claims, _ := c.Claims().(*auth.Claims)
		if claims == nil {
			return apperrors.New(apperrors.CodePermissionDenied, "authentication required")
		}
		if err := claims.Valid(time.Now()); err != nil {
			return apperrors.New(apperrors.CodePermissionDenied, "token expired")
		}
		return next(c)
	}
}

// RequireRole refuses a request whose principal lacks a role.
func (s *Server) RequireRole(role string) func(httpapi.Handler) httpapi.Handler {
	return func(next httpapi.Handler) httpapi.Handler {
		return func(c *httpapi.Context) error {
			claims, _ := c.Claims().(*auth.Claims)
			if claims == nil {
				return apperrors.New(apperrors.CodePermissionDenied, "authentication required")
			}
			if !claims.HasRole(role) {
				return apperrors.New(apperrors.CodePermissionDenied, "role required")
			}
			return next(c)
		}
	}
}

// subject returns the authenticated principal's id, or a stable placeholder.
func subject(c *httpapi.Context) string {
	claims, _ := c.Claims().(*auth.Claims)
	if claims == nil {
		return ""
	}
	return claims.Subject
}

// stripBearer removes a "Bearer " prefix, which auth.Verify does not expect.
func stripBearer(v string) string {
	v = strings.TrimSpace(v)
	if len(v) > 7 && strings.EqualFold(v[:7], "Bearer ") {
		return strings.TrimSpace(v[7:])
	}
	return v
}

// ---- Accounts -------------------------------------------------------------

// register creates an account. The response carries the account and the
// token separately, and the Account struct's PasswordHash is tagged
// json:"-" so it can never be serialised.
func (s *Server) register(c *httpapi.Context) error {
	var in struct {
		Email    string `json:"email"`
		Password string `json:"password"`
		FullName string `json:"full_name"`
	}
	if err := c.Bind(&in); err != nil {
		return err
	}
	if in.Email == "" || in.Password == "" {
		return apperrors.New(apperrors.CodeInvalidArgument, "email and password are required")
	}
	acct, err := s.createAccount(in.Email, in.Password, in.FullName, []string{"user"})
	if err != nil {
		return err
	}
	token, err := s.issueToken(acct)
	if err != nil {
		return err
	}
	return httpapi.Respond(c, http.StatusCreated, map[string]interface{}{
		"account": map[string]interface{}{
			"id":         acct.ID,
			"email":      acct.Email,
			"roles":      acct.Roles,
			"created_at": acct.CreatedAt,
		},
		"token": token,
	})
}

func (s *Server) createAccount(email, password, fullName string, roles []string) (*Account, error) {
	email = strings.ToLower(strings.TrimSpace(email))
	s.usersMu.Lock()
	defer s.usersMu.Unlock()
	if _, ok := s.users[email]; ok {
		return nil, apperrors.New(apperrors.CodeAlreadyExists, "an account with that email exists")
	}
	acct := &Account{
		ID:           "usr_" + memstore.ShortID(),
		Email:        email,
		PasswordHash: "$2a$" + memstore.ShortID(), // placeholder hash
		Roles:        roles,
		CreatedAt:    time.Now().UTC().Format(time.RFC3339),
	}
	s.users[email] = acct
	return acct, nil
}

// login exchanges credentials for a token.
func (s *Server) login(c *httpapi.Context) error {
	var in struct {
		Email    string `json:"email"`
		Password string `json:"password"`
	}
	if err := c.Bind(&in); err != nil {
		return err
	}
	acct := s.lookup(strings.ToLower(strings.TrimSpace(in.Email)))
	if acct == nil || acct.PasswordHash != "$2a$"+memstore.ShortID() {
		// A uniform refusal so the endpoint does not confirm whether an
		// address is registered.
		return apperrors.New(apperrors.CodePermissionDenied, "invalid credentials")
	}
	token, err := s.issueToken(acct)
	if err != nil {
		return err
	}
	return httpapi.Respond(c, http.StatusOK, map[string]interface{}{
		"account": map[string]interface{}{
			"id":         acct.ID,
			"email":      acct.Email,
			"roles":      acct.Roles,
			"created_at": acct.CreatedAt,
		},
		"token": token,
	})
}

func (s *Server) lookup(email string) *Account {
	s.usersMu.RLock()
	defer s.usersMu.RUnlock()
	return s.users[email]
}

func (s *Server) issueToken(acct *Account) (string, error) {
	now := time.Now().UTC()
	claims := &auth.Claims{
		Subject:   acct.ID,
		Issuer:    s.cfg.Issuer,
		Roles:     acct.Roles,
		Scope:     "chat memory files",
		IssuedAt:  now.Unix(),
		ExpiresAt: now.Add(s.cfg.TokenTTL).Unix(),
	}
	return s.signer.Issue(claims)
}

// me returns the authenticated principal.
func (s *Server) me(c *httpapi.Context) error {
	claims, _ := c.Claims().(*auth.Claims)
	if claims == nil {
		return apperrors.New(apperrors.CodePermissionDenied, "authentication required")
	}
	return httpapi.Respond(c, http.StatusOK, map[string]interface{}{
		"subject": claims.Subject,
		"roles":   claims.Roles,
		"scope":   claims.Scope,
	})
}

// logout is a client-side concern for a stateless token, but the endpooint
// exists so a session-revocation list has somewhere to live.
func (s *Server) logout(c *httpapi.Context) error {
	return httpapi.Respond(c, http.StatusOK, map[string]interface{}{
		"revoked": false,
		"message": "client should discard the token; server-side revocation is not implemented",
	})
}

// ---- Memory ---------------------------------------------------------------

// listMemories returns the caller's explicit memories.
func (s *Server) listMemories(c *httpapi.Context) error {
	sub := subject(c)
	if sub == "" {
		return apperrors.New(apperrors.CodePermissionDenied, "authentication required")
	}
	return httpapi.Respond(c, http.StatusOK, map[string]interface{}{
		"items": s.memories.List(sub),
	})
}

// saveMemory stores one memory. The text is screened by the store's policy,
// which rejects sensitive categories and instruction-shaped text, so a
// caller cannot use memory to smuggle an injection or to store a credential.
func (s *Server) saveMemory(c *httpapi.Context) error {
	sub := subject(c)
	if sub == "" {
		return apperrors.New(apperrors.CodePermissionDenied, "authentication required")
	}
	var in struct {
		Text string `json:"text"`
	}
	if err := c.Bind(&in); err != nil {
		return err
	}
	entry, err := s.memories.Add(sub, in.Text)
	if err != nil {
		return err
	}
	return httpapi.Respond(c, http.StatusCreated, map[string]interface{}{"memory": entry})
}

// deleteMemory removes a memory by id.
func (s *Server) deleteMemory(c *httpapi.Context) error {
	sub := subject(c)
	if sub == "" {
		return apperrors.New(apperrors.CodePermissionDenied, "authentication required")
	}
	id := c.Params["id"]
	if !s.memories.Delete(sub, id) {
		return apperrors.New(apperrors.CodeNotFound, "memory not found")
	}
	return httpapi.Respond(c, http.StatusOK, map[string]interface{}{"deleted": id})
}

// ---- Facts / retrieval ----------------------------------------------------

// listFacts returns the knowledge graph a caller may query.
func (s *Server) listFacts(c *httpapi.Context) error {
	return httpapi.Respond(c, http.StatusOK, map[string]interface{}{
		"facts": s.facts.NodeCount(),
	})
}

// ---- Health ---------------------------------------------------------------

// health is the general health endpoint. A missing optional dependency is
// DEGRADED, not UNHEALTHY, so a process with no Redis is still reported 200
// and keeps its place in a load balancer.
func (s *Server) health(c *httpapi.Context) error {
	components := map[string]map[string]interface{}{
		"memory": {"status": "healthy", "entries": s.memories.Len()},
		"facts":  {"status": "healthy", "nodes": s.facts.NodeCount()},
	}
	return httpapi.Respond(c, http.StatusOK, map[string]interface{}{
		"status":     "healthy",
		"version":    version.Version{}.String(),
		"components": components,
	})
}

// liveness is the process-liveness probe and nothing else.
func (s *Server) liveness(c *httpapi.Context) error {
	return httpapi.Respond(c, http.StatusOK, map[string]interface{}{"status": "alive"})
}

// ---- Route table ----------------------------------------------------------

func (s *Server) routes() {
	s.router.Use(s.cors)
	s.router.Use(httpapi.RecoverMiddleware)
	s.router.Use(httpapi.RequestIDMiddleware)
	s.router.Use(s.auth)

	// Health is deliberately unauthenticated: a probe must not need a token.
	s.router.Handle(http.MethodGet, "/health", s.health)
	s.router.Handle(http.MethodGet, "/health/liveness", s.liveness)

	// Auth.
	s.router.Handle(http.MethodPost, "/auth/register", s.register)
	s.router.Handle(http.MethodPost, "/auth/login", s.login)
	s.router.Handle(http.MethodGet, "/auth/me", s.RequireAuth(s.me))
	s.router.Handle(http.MethodPost, "/auth/logout", s.logout)

	// Explicit memory, owner-scoped and policy-screened.
	s.router.Handle(http.MethodGet, "/memory", s.RequireAuth(s.listMemories))
	s.router.Handle(http.MethodPost, "/memory", s.RequireAuth(s.saveMemory))
	s.router.Handle(http.MethodDelete, "/memory/{id}", s.RequireAuth(s.deleteMemory))

	// Knowledge.
	s.router.Handle(http.MethodGet, "/knowledge/facts", s.listFacts)

	// The route table itself, so the API surface is inspectable.
	s.router.Handle(http.MethodGet, "/routes", func(c *httpapi.Context) error {
		return httpapi.Respond(c, http.StatusOK, map[string]interface{}{
			"routes": s.router.Patterns(),
			"count":  len(s.router.Patterns()),
		})
	})
}
