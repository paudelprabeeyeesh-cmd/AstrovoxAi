package main

import (
	"time"

	"github.com/astrovox/astrovox/internal/api/config"
)

// testConfig returns a configuration that validates without reading the
// environment, so a developer's shell cannot change what a test expects.
//
// The spend limit is deliberately generous so the fixture requests are not
// refused; the refusal behaviour has its own test with a tight budget.
func testConfig() *config.Config {
	return &config.Config{
		Addr:                ":8080",
		JWTSecret:           "0123456789abcdef0123456789abcdef",
		Issuer:              "test",
		TokenTTL:            time.Hour,
		Environment:         "test",
		AllowedOrigins:      []string{"http://localhost:5173"},
		TrustProxyHeaders:   false,
		SpendLimitUSD:       100.0,
		TenantSpendLimitUSD: 500.0,
		LogLevel:            "error",
		ShutdownTimeout:     30 * time.Second,
		MaxBodyBytes:        8 << 20,
		RateLimitPerMin:     120,
	}
}
