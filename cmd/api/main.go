// Command api runs the Astrovox AI API server.
//
// It is the single entry point that wires the Go packages into a runnable
// service: config validated at startup, every subsystem mounted, and a
// graceful drain on SIGTERM so an in-flight request is not dropped.
//
// A missing or placeholder secret refuses to start rather than defaulting to
// a weak one, which is the fail-fast rule the Python backend lacked.
package main

import (
	"context"
	"errors"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/astrovox/astrovox/internal/api/config"
	"github.com/astrovox/astrovox/internal/api/logging"
	"github.com/astrovox/astrovox/internal/auth"
	"github.com/astrovox/astrovox/internal/conversations"
	"github.com/astrovox/astrovox/internal/httpapi"
	"github.com/astrovox/astrovox/internal/memstore"
	"github.com/astrovox/astrovox/internal/retrieval"
	"github.com/astrovox/astrovox/internal/tools/agent"
)

func main() {
	log := logging.New("astrovox-api")
	log.SetLevel(logging.ParseLevel(os.Getenv("LOG_LEVEL")))

	cfg, err := config.Load()
	if err != nil {
		// A misconfiguration is a deployment failure, so it is logged and the
		// process exits rather than starting with a guess baked in.
		log.Error("configuration rejected").Err(err).Write()
		os.Exit(1)
	}

	router := httpapi.NewRouter()
	if err := mount(router, cfg, log); err != nil {
		log.Error("server construction failed").Err(err).Write()
		os.Exit(1)
	}

	httpServer := &http.Server{
		Addr:              cfg.Addr,
		Handler:           router,
		ReadHeaderTimeout: 10 * time.Second,
		ReadTimeout:       30 * time.Second,
		// 120s exceeds the LLM stream budget, so a long stream is not cut off
		// by the write deadline.
		WriteTimeout: 120 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		log.Info("listening").
			Field("addr", cfg.Addr).
			Field("environment", cfg.Environment).
			Field("routes", len(router.Patterns())).
			Write()
		if err := httpServer.ListenAndServe(); err != nil &&
			!errors.Is(err, http.ErrServerClosed) {
			log.Error("listen failed").Err(err).Write()
			os.Exit(1)
		}
	}()

	<-stop
	log.Info("shutting down").
		Field("drain_seconds", cfg.ShutdownTimeout.Seconds()).
		Write()

	ctx, cancel := context.WithTimeout(context.Background(), cfg.ShutdownTimeout)
	defer cancel()
	if err := httpServer.Shutdown(ctx); err != nil {
		log.Error("drain did not finish in time").Err(err).Write()
		os.Exit(1)
	}
	log.Info("stopped").Write()
}

// mount wires every subsystem into the router.
//
// Health is registered unauthenticated, because a probe must not need a
// token. Every other route is mounted behind requireAuth.
func mount(router *httpapi.Router, cfg *config.Config, log *logging.Logger) error {
	router.Use(recoverMiddleware(log))

	signer := auth.NewJWTSigner(cfg.JWTSecret, cfg.Issuer, cfg.TokenTTL)
	if signer == nil {
		return errors.New("the JWT signer could not be constructed")
	}

	// The auth middleware attaches the caller's claims to the context. It is
	// applied to the whole router so a route cannot forget it; requireAuth is
	// what refuses an anonymous request.
	router.Use(authMiddleware(signer))

	mountHealth(router)

	// In-process stores. The durable store is a schema decision, and an
	// in-memory one makes the boundary testable today.
	memories := memstore.New(10_000)
	chats := conversations.New(10_000)
	corpus := retrieval.NewCorpus()
	index := retrieval.NewIndex(corpus, retrieval.NewHashEmbeddable(64))

	mountAuth(router, signer, cfg)
	mountChat(router, signer, &referenceVendor{}, cfg)
	mountConversations(router, signer, chats)
	mountMemory(router, signer, memories)
	mountRetrieval(router, signer, corpus, index)
	mountTools(router, signer, stockRegistry(), stockExecutor(), agentCfg())
	return nil
}

// recoverMiddleware converts a panic into a 500 envelope rather than a
// dropped connection. It is applied through the router's own chain so a
// panic in any handler is covered.
func recoverMiddleware(log *logging.Logger) func(httpapi.Handler) httpapi.Handler {
	return func(next httpapi.Handler) httpapi.Handler {
		return func(c *httpapi.Context) (err error) {
			defer func() {
				if rec := recover(); rec != nil {
					// The panic value is logged, never returned: it can carry
					// internal state.
					log.Error("request panicked").
						Field("panic", rec).
						Field("request_id", c.RequestID).
						Field("path", c.Request.URL.Path).
						Write()
					_ = httpapi.Respond(c, http.StatusInternalServerError,
						map[string]string{"error": "internal error"})
				}
			}()
			return next(c)
		}
	}
}

// mountHealth registers the health surface. Every route here is
// unauthenticated because a probe must not be challenged.
func mountHealth(router *httpapi.Router) {
	router.Handle(http.MethodGet, "/health", func(c *httpapi.Context) error {
		return httpapi.Respond(c, http.StatusOK, map[string]string{"status": "healthy"})
	})
	router.Handle(http.MethodGet, "/health/liveness", func(c *httpapi.Context) error {
		return httpapi.Respond(c, http.StatusOK, map[string]string{"status": "alive"})
	})
	router.Handle(http.MethodGet, "/health/startup", func(c *httpapi.Context) error {
		return httpapi.Respond(c, http.StatusOK, map[string]string{"status": "started"})
	})
}

// agentCfg returns the default agent configuration.
func agentCfg() agent.Config {
	return agent.Config{
		Name:     "assistant",
		Limits:   agent.DefaultLimits(),
		Approver: agent.DenyApprover{},
	}
}
