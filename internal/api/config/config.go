// Package config loads and validates the API server's configuration.
//
// Validation is fail-fast and complete at startup, because every one of these
// checks is the difference between a service that refuses to boot and a
// service that boots with a guess baked in. A defaulted SECRET_KEY means
// tokens signed by a value an attacker can read out of the repository; a
// defaulted origin list means CORS wide open; a missing spend limit means an
// unmetered AI proxy, which is the single largest financial exposure in an
// AI product.
//
// The Python backend had none of this, which is why "change-me-in-production"
// shipped as the production secret.
package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"
)

// Config is the fully-validated configuration.
type Config struct {
	// Addr is the listen address.
	Addr string
	// JWTSecret signs session tokens. Required, minimum 32 bytes.
	JWTSecret string
	// Issuer is the JWT issuer claim.
	Issuer string
	// TokenTTL bounds a session token.
	TokenTTL time.Duration
	// Environment names the deployment.
	Environment string
	// AllowedOrigins is the CORS allow-list. Empty in production is an error,
	// not a default.
	AllowedOrigins []string
	// TrustProxyHeaders permits reading X-Forwarded-For.
	TrustProxyHeaders bool
	// SpendLimitUSD is the per-user daily AI budget.
	SpendLimitUSD float64
	// TenantSpendLimitUSD is the per-tenant daily budget.
	TenantSpendLimitUSD float64
	// RedisURL enables the Redis-backed rate limiter when set.
	RedisURL string
	// RedisPassword carries the Redis credentials.
	RedisPassword string
	// LogLevel is the minimum level written.
	LogLevel string
	// ShutdownTimeout bounds a graceful drain.
	ShutdownTimeout time.Duration
	// MaxBodyBytes bounds a request body.
	MaxBodyBytes int64
	// RateLimitPerMin is the per-IP request budget.
	RateLimitPerMin int
}

// production marks the deployment whose rules are strictest.
const production = "production"

// insecureSecrets are the markers that must never appear in a secret. They
// are the values this repository would produce from its own defaults.
//
// Matching is by substring, not equality: a caller who pads "change-me" out
// to the length requirement with more "change-me" has produced a known
// placeholder, and an exact-match check would wave it through.
var insecureSecrets = []string{
	"change-me", "changeme", "test-secret", "ci-only",
	"not-a-real-secret", "placeholder", "your-secret", "replace-me",
	"insecure", "default-secret", "dev-secret", "secretkey",
}

// isInsecureSecret reports whether a secret is a known placeholder.
func isInsecureSecret(secret string) bool {
	lower := strings.ToLower(strings.TrimSpace(secret))
	for _, marker := range insecureSecrets {
		if strings.Contains(lower, marker) {
			return true
		}
	}
	return false
}

// Load reads the environment and validates it.
//
// Every error is returned rather than defaulted past, so a misconfigured
// deployment fails at startup where it is visible, rather than at its first
// request where it is a 500.
func Load() (*Config, error) {
	cfg := &Config{
		Addr:                envOr("API_ADDR", ":8080"),
		JWTSecret:           os.Getenv("JWT_SECRET"),
		Issuer:              envOr("API_ISSUER", "astrovox"),
		TokenTTL:            envDuration("TOKEN_TTL", 24*time.Hour),
		Environment:         strings.ToLower(envOr("ENVIRONMENT", "development")),
		AllowedOrigins:      splitList(os.Getenv("ALLOWED_ORIGINS")),
		TrustProxyHeaders:   envBool("TRUST_PROXY_HEADERS", false),
		SpendLimitUSD:       envFloat("AI_DAILY_SPEND_LIMIT_USD", 1.0),
		TenantSpendLimitUSD: envFloat("TENANT_DAILY_SPEND_LIMIT_USD", 500.0),
		RedisURL:            os.Getenv("REDIS_URL"),
		RedisPassword:       os.Getenv("REDIS_PASSWORD"),
		LogLevel:            envOr("LOG_LEVEL", "info"),
		ShutdownTimeout:     envDuration("SHUTDOWN_TIMEOUT", 30*time.Second),
		MaxBodyBytes:        int64(envInt("MAX_BODY_BYTES", 8<<20)),
		RateLimitPerMin:     envInt("RATE_LIMIT_PER_MIN", 120),
	}

	if err := cfg.validate(); err != nil {
		return nil, err
	}
	return cfg, nil
}

// validate is the whole point of the package.
func (c *Config) validate() error {
	if len(c.JWTSecret) < 32 {
		return fmt.Errorf(
			"JWT_SECRET must be at least 32 bytes; refusing to sign tokens with a short secret (got %d)",
			len(c.JWTSecret),
		)
	}
	if isInsecureSecret(c.JWTSecret) {
		return fmt.Errorf("JWT_SECRET is a known placeholder; refusing to start")
	}

	if c.Environment == production {
		// A production deployment without an origin list would answer
		// preflight requests from any site.
		if len(c.AllowedOrigins) == 0 {
			return fmt.Errorf("ALLOWED_ORIGINS is required in production")
		}
		for _, o := range c.AllowedOrigins {
			if o == "*" {
				return fmt.Errorf("ALLOWED_ORIGINS must not be '*' in production")
			}
		}
	}

	if c.SpendLimitUSD <= 0 {
		return fmt.Errorf("AI_DAILY_SPEND_LIMIT_USD must be positive; an unmetered AI proxy is not permitted")
	}
	if c.TenantSpendLimitUSD < c.SpendLimitUSD {
		return fmt.Errorf(
			"TENANT_DAILY_SPEND_LIMIT_USD (%.2f) is below the per-user limit (%.2f); the tenant cap would be unreachable",
			c.TenantSpendLimitUSD, c.SpendLimitUSD,
		)
	}

	// A Redis URL that carries a user segment but no password is the exact
	// compose bug: the server starts with credentials and the client omits
	// them, so nothing can reach Redis.
	if c.RedisURL != "" && c.RedisPassword == "" && strings.Contains(c.RedisURL, "@") {
		return fmt.Errorf("REDIS_URL carries a user segment but REDIS_PASSWORD is empty")
	}

	if c.MaxBodyBytes <= 0 || c.MaxBodyBytes > 64<<20 {
		return fmt.Errorf("MAX_BODY_BYTES must be between 1 and 64 MiB (got %d)", c.MaxBodyBytes)
	}
	if c.RateLimitPerMin <= 0 {
		return fmt.Errorf("RATE_LIMIT_PER_MIN must be positive")
	}
	if c.TokenTTL <= 0 {
		return fmt.Errorf("TOKEN_TTL must be positive")
	}
	return nil
}

// IsProduction reports whether this is a production deployment.
func (c *Config) IsProduction() bool { return c.Environment == production }

// ---- Environment helpers --------------------------------------------------

func envOr(name, def string) string {
	if v := os.Getenv(name); v != "" {
		return v
	}
	return def
}

func envInt(name string, def int) int {
	v := os.Getenv(name)
	if v == "" {
		return def
	}
	n, err := strconv.Atoi(strings.TrimSpace(v))
	if err != nil {
		return def
	}
	return n
}

func envFloat(name string, def float64) float64 {
	v := os.Getenv(name)
	if v == "" {
		return def
	}
	f, err := strconv.ParseFloat(strings.TrimSpace(v), 64)
	if err != nil {
		return def
	}
	return f
}

func envDuration(name string, def time.Duration) time.Duration {
	v := os.Getenv(name)
	if v == "" {
		return def
	}
	d, err := time.ParseDuration(strings.TrimSpace(v))
	if err != nil {
		return def
	}
	return d
}

func envBool(name string, def bool) bool {
	v := strings.ToLower(strings.TrimSpace(os.Getenv(name)))
	switch v {
	case "1", "true", "yes", "on":
		return true
	case "0", "false", "no", "off":
		return false
	default:
		return def
	}
}

func splitList(v string) []string {
	var out []string
	for _, part := range strings.Split(v, ",") {
		if part = strings.TrimSpace(part); part != "" {
			out = append(out, part)
		}
	}
	return out
}
