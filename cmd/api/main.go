// Command api runs the Astrovox API server.
//
// It exists so the boundary has one runnable entry point. The engine
// packages are libraries; this command wires them, reads configuration
// from the environment, and serves HTTP.
//
// Usage:
//
//	api -addr :8080 -jwt-secret "$SECRET"
//
// A missing secret is refused rather than defaulted to a weak value, so a
// deployment cannot accidentally issue tokens signed by a predictable key.
// That is the same fail-fast rule the Python backend was missing.
package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/astrovox/astrovox/internal/apiserver"
)

func main() {
	addr := flag.String("addr", envOr("API_ADDR", ":8080"), "listen address")
	secret := flag.String("jwt-secret", os.Getenv("JWT_SECRET"), "HMAC secret for session tokens")
	issuer := flag.String("issuer", envOr("API_ISSUER", "astrovox"), "JWT issuer claim")
	origins := flag.String("origins", os.Getenv("ALLOWED_ORIGINS"), "comma-separated CORS allow-list")
	flag.Parse()

	if *secret == "" {
		log.Fatal("JWT_SECRET or -jwt-secret is required; refusing to start with a weak default")
	}

	cfg := apiserver.DefaultConfig()
	cfg.JWTSecret = *secret
	cfg.Issuer = *issuer
	if *origins != "" {
		cfg.AllowedOrigins = splitComma(*origins)
	}

	srv, err := apiserver.New(cfg)
	if err != nil {
		log.Fatalf("building the server failed: %v", err)
	}

	httpServer := &http.Server{
		Addr:              *addr,
		Handler:           srv.Handler(),
		ReadHeaderTimeout: 10 * time.Second,
		ReadTimeout:       30 * time.Second,
		// 120s exceeds the LLM stream budget, so a long stream is not cut
		// off by the write timeout.
		WriteTimeout: 120 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	// Graceful shutdown, so in-flight requests finish before the process
	// exits. Kubernetes sends SIGTERM, not SIGINT.
	shutdown := make(chan os.Signal, 1)
	signal.Notify(shutdown, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-shutdown
		fmt.Println("shutdown: draining in-flight requests")
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		_ = httpServer.Shutdown(ctx)
	}()

	fmt.Printf("api listening on %s (routes: %d)\n", *addr, len(srv.Router().Patterns()))
	if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("listen failed: %v", err)
	}
	fmt.Println("api stopped")
}

// envOr reads an environment variable with a fallback.
func envOr(name, def string) string {
	if v := os.Getenv(name); v != "" {
		return v
	}
	return def
}

// splitComma splits a comma-separated list, dropping empty entries.
func splitComma(s string) []string {
	var out []string
	for _, part := range strings.Split(s, ",") {
		if part = strings.TrimSpace(part); part != "" {
			out = append(out, part)
		}
	}
	return out
}
