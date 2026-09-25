# Changelog

All notable changes from the production-readiness pass. This builds on the
earlier audit PR (#2), which fixed the broken Vite build, hardened CORS/secrets,
purged ~360 junk files, and added the first DB migration.

## [2.1.0] — Production Engineering Pass (2026-06-29)

### Added
- **Rate Limiting**: Implemented slowapi for backend rate limiting
  - Signup: 5 requests/minute
  - Login: 10 requests/minute
  - Chat messages: 30 requests/minute
- **CI/CD Pipeline**: Complete GitHub Actions workflow (`.github/workflows/ci.yml`)
  - Frontend lint & build job
  - Backend lint & test job
  - Secret scanning with TruffleHog
  - Dependency auditing (npm + safety)
  - Docker build testing
- **Docker Configuration**: Production-ready containerization
  - `Dockerfile.backend` - Python 3.9-slim with health checks
  - `Dockerfile.frontend` - Multi-stage Node 18-alpine + Nginx
  - `docker-compose.yml` - Multi-container orchestration
  - `nginx.conf` - Production reverse proxy with security headers
- **Deployment Documentation**: Comprehensive `DEPLOYMENT.md` guide
  - Docker deployment instructions
  - Cloud platform deployment options
  - Security considerations
  - Scaling recommendations

### Fixed
- **CORS Hardening**: Restrict origins to production domains
- **Secret Management**: Remove hardcoded secrets from docker-compose
- **Logging**: Add structured JSON logging with request tracing
- **Security Headers**: HSTS, CSP, X-Frame-Options via Nginx
- **Rate Limiting**: Add slowapi to backend with configurable limits

### Changed
- **Structured Logging**: Implemented JSONFormatter for production logs
- **Input Validation**: Added Pydantic `Field` constraints to prevent oversized payloads
- **Error Messages**: Sanitized user-facing errors to prevent information leakage

### Security
- **Dependency Audit**: Run `pip-audit` and `npm audit` in CI
- **Secret Scanning**: Add TruffleHog to detect committed credentials
- **Rate Limiting**: Prevent credential stuffing and DoS
- **CORS**: Restrict to production domains only

---

## [2.2.0] — Enterprise Grade (2026-09-25)

### Added
- **Service Mesh**: Istio configuration for traffic management, mTLS, and circuit breaking
  - VirtualService, DestinationRule, Gateway, AuthorizationPolicy, PeerAuthentication
- **Progressive Delivery**: Canary and blue-green deployment strategies
  - ArgoCD AnalysisTemplates for automated promotion
  - Traffic splitting with Istio VirtualService
- **Infrastructure Drift Detection**: Terraform and Kubernetes drift detection
- **Distributed Tracing**: OpenTelemetry integration for end-to-end observability
- **Enhanced Failover**: Database connection pooling with automatic failover and circuit breaking
- **FinOps Automation**: Cost optimization, budget management, and anomaly detection
- **Justfile**: Development commands for lint, test, migrate, and deploy
- **HPA**: Horizontal Pod Autoscaler for production workloads
- **VPA**: Vertical Pod Autoscaler for resource optimization
- **NetworkPolicy**: Kubernetes network policies for zero-trust
- **PodDisruptionBudget**: High availability during node maintenance
- **ServiceMonitor**: Prometheus monitoring for Kubernetes services
- **Sidecar Injection**: Istio sidecar injection for service mesh
- **mTLS**: STRICT mode for service-to-service communication
- **AuthorizationPolicy**: Istio authorization for API access control
- **DestinationRule**: Circuit breaking, outlier detection, and load balancing
- **VirtualService**: Traffic routing, retries, and fault injection
- **Canary Deployment**: Automated canary analysis with Prometheus metrics
- **Blue-Green Deployment**: Blue-green service switching with preview
- **Progressive Delivery Manager**: Feature flags, canary steps, and analysis
- **Service Mesh Manager**: Istio manifest generation
- **OpenTelemetry Tracer**: Span creation, attribute tracking, OTLP export
- **Failover Manager**: Circuit breaker, failure counting, state management
- **Drift Detector**: Terraform and Kubernetes resource drift detection
- **FinOps Manager**: Cost tracking, budget management, anomaly detection
- **Kubernetes Manifests**: Production-grade cluster resources
- **Istio Manifests**: Service mesh configuration
- **Canary Manifests**: Canary deployment and analysis
- **Blue-Green Manifests**: Blue-green service and deployment

### Changed
- **CI/CD**: Enhanced with security scanning, progressive delivery, and chaos tests
- **Infrastructure**: Added service mesh, drift detection, and cost optimization
- **Observability**: Added OpenTelemetry distributed tracing
- **Database**: Added connection pooling with automatic failover
- **Platform**: Added FinOps automation and cost visibility

### Removed
- **Merge Conflicts**: Resolved in database.py, logging_config.py, telemetry.py, CHANGELOG.md, AUDIT_REPORT.md
