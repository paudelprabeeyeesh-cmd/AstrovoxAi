package config

import (
	"os"
	"testing"
	"time"
)

// envKeys are every key the loader reads, cleared before each test so a
// developer's shell does not leak into the result.
var envKeys = []string{
	"JWT_SECRET", "ENVIRONMENT", "ALLOWED_ORIGINS", "TOKEN_TTL",
	"API_ADDR", "API_ISSUER", "LOG_LEVEL", "REDIS_URL", "REDIS_PASSWORD",
	"MAX_BODY_BYTES", "RATE_LIMIT_PER_MIN", "TRUST_PROXY_HEADERS",
	"AI_DAILY_SPEND_LIMIT_USD", "TENANT_DAILY_SPEND_LIMIT_USD",
	"SHUTDOWN_TIMEOUT",
}

// validSecret is 32 bytes and is not a known placeholder.
const validSecret = "0123456789abcdef0123456789abcdef"

func valid(t *testing.T) {
	t.Helper()
	for _, k := range envKeys {
		os.Unsetenv(k)
	}
	t.Setenv("JWT_SECRET", validSecret)
	t.Setenv("ENVIRONMENT", "development")
	t.Setenv("ALLOWED_ORIGINS", "http://localhost:5173")
}

func TestLoadAcceptsAValidSecret(t *testing.T) {
	valid(t)
	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load failed: %v", err)
	}
	if len(cfg.JWTSecret) != 32 {
		t.Fatalf("secret length = %d, want 32", len(cfg.JWTSecret))
	}
}

func TestLoadRejectsAShortSecret(t *testing.T) {
	valid(t)
	t.Setenv("JWT_SECRET", "short")
	if _, err := Load(); err == nil {
		t.Fatal("a short secret was accepted")
	}
}

func TestLoadRejectsAPlaceholderSecret(t *testing.T) {
	// These are the values this repository's own defaults would produce. Each
	// is padded past the length check, so the refusal is by name and not by
	// length.
	for _, placeholder := range []string{
		"change-me", "change-me-in-production", "changeme",
		"test-secret", "test-secret-key-for-ci-only",
		"ci-only-not-a-real-secret", "placeholder", "your-secret-here",
	} {
		secret := placeholder
		for len(secret) < 48 {
			secret += placeholder
		}
		valid(t)
		t.Setenv("JWT_SECRET", secret)
		if _, err := Load(); err == nil {
			t.Fatalf("placeholder secret %q was accepted", placeholder)
		}
	}
}

func TestProductionRequiresAnOriginList(t *testing.T) {
	valid(t)
	os.Unsetenv("ALLOWED_ORIGINS")
	t.Setenv("ENVIRONMENT", "production")
	if _, err := Load(); err == nil {
		t.Fatal("production started without ALLOWED_ORIGINS")
	}
}

func TestProductionRefusesAWildcardOrigin(t *testing.T) {
	valid(t)
	t.Setenv("ENVIRONMENT", "production")
	t.Setenv("ALLOWED_ORIGINS", "*")
	if _, err := Load(); err == nil {
		t.Fatal("production accepted a wildcard origin")
	}
}

func TestProductionAcceptsExplicitOrigins(t *testing.T) {
	valid(t)
	t.Setenv("ENVIRONMENT", "production")
	t.Setenv("ALLOWED_ORIGINS", "https://app.example.com, https://api.example.com")
	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load failed: %v", err)
	}
	if len(cfg.AllowedOrigins) != 2 {
		t.Fatalf("%d origins, want 2", len(cfg.AllowedOrigins))
	}
}

func TestSpendLimitMustBePositive(t *testing.T) {
	// An unmetered AI proxy is the single largest financial exposure in an
	// AI product, so a zero budget must refuse to boot.
	valid(t)
	t.Setenv("AI_DAILY_SPEND_LIMIT_USD", "0")
	if _, err := Load(); err == nil {
		t.Fatal("a zero spend limit was accepted")
	}
}

func TestTenantLimitMustCoverTheUserLimit(t *testing.T) {
	valid(t)
	t.Setenv("AI_DAILY_SPEND_LIMIT_USD", "10")
	t.Setenv("TENANT_DAILY_SPEND_LIMIT_USD", "1")
	if _, err := Load(); err == nil {
		t.Fatal("a tenant cap below the user cap was accepted")
	}
}

func TestAPasswordlessRedisURLIsAccepted(t *testing.T) {
	// The compose bug was a server started with credentials and a client URL
	// that omitted them. That combination is refused; a genuinely open
	// Redis with no user segment is not.
	valid(t)
	t.Setenv("REDIS_URL", "redis://redis:6379/0")
	if _, err := Load(); err != nil {
		t.Fatalf("Load failed: %v", err)
	}
}

func TestARedisURLWithAUserSegmentAndNoPasswordIsRefused(t *testing.T) {
	valid(t)
	t.Setenv("REDIS_URL", "redis://:secret@redis:6379/0")
	if _, err := Load(); err == nil {
		t.Fatal("a Redis URL with a user segment and no password was accepted")
	}
}

func TestABalancedRedisConfigurationIsAccepted(t *testing.T) {
	valid(t)
	t.Setenv("REDIS_URL", "redis://:secret@redis:6379/0")
	t.Setenv("REDIS_PASSWORD", "secret")
	if _, err := Load(); err != nil {
		t.Fatalf("Load failed: %v", err)
	}
}

func TestMaxBodyBytesIsBounded(t *testing.T) {
	valid(t)
	t.Setenv("MAX_BODY_BYTES", "0")
	if _, err := Load(); err == nil {
		t.Fatal("a zero body limit was accepted")
	}

	valid(t)
	t.Setenv("MAX_BODY_BYTES", "134217729") // 64 MiB + 1
	if _, err := Load(); err == nil {
		t.Fatal("an unbounded body limit was accepted")
	}
}

func TestDefaultsAreUsedWhenTheEnvironmentIsSilent(t *testing.T) {
	valid(t)
	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load failed: %v", err)
	}
	if cfg.TokenTTL != 24*time.Hour {
		t.Fatalf("token ttl = %s, want the default", cfg.TokenTTL)
	}
	if cfg.LogLevel != "info" {
		t.Fatalf("log level = %s, want the default", cfg.LogLevel)
	}
	if cfg.RateLimitPerMin != 120 {
		t.Fatalf("rate limit = %d, want the default", cfg.RateLimitPerMin)
	}
	if cfg.IsProduction() {
		t.Fatal("an empty ENVIRONMENT was treated as production")
	}
}

func TestIsProductionChecksTheNameCaseInsensitively(t *testing.T) {
	valid(t)
	t.Setenv("ENVIRONMENT", "PRODUCTION")
	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load failed: %v", err)
	}
	if !cfg.IsProduction() {
		t.Fatal("a case-insensitive ENVIRONMENT was not recognised as production")
	}
}
