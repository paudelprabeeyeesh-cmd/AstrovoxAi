# AstrovoxAI Documentation

Welcome to the AstrovoxAI documentation. This directory contains comprehensive guides for developers, operators, and contributors.

## Documentation Index

### Getting Started
- [README.md](../README.md) — Project overview, quick start, and feature tour
- [QUICK_START.md](QUICK_START.md) — Fast-track setup guide
- [SETUP.md](SETUP.md) — Detailed environment setup
- [ONBOARDING.md](ONBOARDING.md) — New team member onboarding
- [LOCAL_DEV.md](LOCAL_DEV.md) — Local development workflow

### Core Documentation
- [API.md](API.md) — Complete REST API reference with examples
- [ARCHITECTURE.md](ARCHITECTURE.md) — System design, data flow, and module breakdown
- [DEPLOYMENT.md](DEPLOYMENT.md) — Production deployment, Docker, Kubernetes, CI/CD
- [CONTRIBUTING.md](CONTRIBUTING.md) — Contribution guidelines, code standards, PR process
- [ROADMAP.md](roadmap.md) — Strategic direction and planned features

### Advanced Topics
- [SDK.md](SDK.md) — Python and TypeScript SDK usage
- [SDK_QUICKSTART.md](SDK_QUICKSTART.md) — Quick SDK integration guide
- [PLUGIN_DEVELOPER_GUIDE.md](PLUGIN_DEVELOPER_GUIDE.md) — Building plugins and extensions
- [WEBHOOKS.md](WEBHOOKS.md) — Webhook configuration and events
- [INTEGRATIONS.md](INTEGRATIONS.md) — Third-party integrations
- [EXTENSIONS.md](extensions.md) — Browser and IDE extensions
- [Extension Framework](extension-framework.md) — Extension SDK and manifest guide

### Developer Experience
- [API Playground](API_PLAYGROUND.md) — Interactive API explorer
- [Analytics](analytics.md) — Platform analytics and usage insights
- [Architecture Diagrams](architecture_diagrams.md) — System and data flow diagrams
- [Tutorials](tutorials.md) — Step-by-step integration guides
- [Docs Generator](docs_generator.py) — Automated documentation generation

### Operations
- [TESTING.md](TESTING.md) — Test strategy and execution
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — Common issues and solutions
- [MONITORING.md](MONITORING.md) — Observability, alerts, and dashboards
- [SECURITY_BEST_PRACTICES.md](SECURITY_BEST_PRACTICES.md) — Security hardening guide
- [SECURITY_AUDIT.md](SECURITY_AUDIT.md) — Security audit reports
- [ON_CALL.md](on_call.md) — On-call runbook

### Production Readiness
- [Runbooks Index](runbooks/production-runbook-index.md) — All operational runbooks
- [Incident Response](runbooks/incident-response.md) — Incident management procedures
- [Automated Rollback](runbooks/automated-rollback.md) — Rollback automation
- [Backup Validation](runbooks/backup-validation.md) — Backup integrity checks
- [Disaster Recovery](runbooks/disaster-recovery-drill.md) — DR drill procedures
- [Cost Optimization](runbooks/cost-optimization.md) — Cost monitoring and optimization
- [Capacity Planning](runbooks/capacity-planning.md) — Resource forecasting
- [SLO Management](runbooks/slo-management.md) — SLO/SLA tracking and error budgets

### Specialized Guides
- [DATABASE_DESIGN.md](DATABASE_DESIGN.md) — Schema design and migrations
- [DATA_FLOW.md](DATA_FLOW.md) — Data pipeline architecture
- [performance-baseline.md](performance-baseline.md) — Performance benchmarks
- [quantization.md](quantization.md) — Model quantization guide
- [robotics.md](robotics.md) — Robotics integration
- [safety.md](safety.md) — AI safety and alignment
- [training.md](training.md) — Model training pipelines

## Quick Navigation

| Role | Start Here |
|------|------------|
| New Developer | [QUICK_START.md](QUICK_START.md) → [SETUP.md](SETUP.md) → [CONTRIBUTING.md](CONTRIBUTING.md) |
| Backend Engineer | [API.md](API.md) → [ARCHITECTURE.md](ARCHITECTURE.md) → [DATABASE_DESIGN.md](DATABASE_DESIGN.md) |
| Frontend Engineer | [README.md](../README.md) → [SDK.md](SDK.md) |
| DevOps / SRE | [DEPLOYMENT.md](DEPLOYMENT.md) → [MONITORING.md](MONITORING.md) → [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |
| Product Manager | [ROADMAP.md](roadmap.md) → [API.md](API.md) |
| Security Engineer | [SECURITY_BEST_PRACTICES.md](SECURITY_BEST_PRACTICES.md) → [SECURITY_AUDIT.md](SECURITY_AUDIT.md) |

## Documentation Standards

- All public APIs must be documented in [API.md](API.md)
- Architecture decisions are recorded in `docs/adr/`
- Breaking changes follow [api_versioning_policy.md](api_versioning_policy.md)
- Security incidents follow [postmortem_template.md](postmortem_template.md)

## Contributing to Docs

Found a gap or error? Please open an issue or submit a PR following [CONTRIBUTING.md](CONTRIBUTING.md).
