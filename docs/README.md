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
- [part2-implementation.md](part2-implementation.md) — Advanced AI implementation guide
- [agents.md](agents.md) — Autonomous agents framework
- [inference.md](inference.md) — High-performance inference engine
- [training.md](training.md) — Distributed training and RLHF
- [safety.md](safety.md) — AI safety, moderation, and alignment
- [robotics.md](robotics.md) — Robotics integration with ROS2
- [enterprise.md](enterprise.md) — Enterprise platform features
- [sdk.md](sdk.md) — Python, TypeScript, Go, Rust SDKs and CLI
- [extensions.md](extensions.md) — IDE and browser extensions
- [SDK_QUICKSTART.md](SDK_QUICKSTART.md) — Quick SDK integration guide
- [PLUGIN_DEVELOPER_GUIDE.md](PLUGIN_DEVELOPER_GUIDE.md) — Building plugins and extensions
- [WEBHOOKS.md](WEBHOOKS.md) — Webhook configuration and events
- [INTEGRATIONS.md](INTEGRATIONS.md) — Third-party integrations
- [Extension Framework](extension-framework.md) — Extension SDK and manifest guide

### Developer Experience
- [API Playground](API_PLAYGROUND.md) — Interactive API explorer
- [Developer Portal](DEVELOPER_PORTAL.md) — Unified control plane for ecosystem
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
- [alerting.md](alerting.md) — Alert configuration
- [on_call.md](on_call.md) — On-call procedures

### Production Readiness
- [Runbooks Index](runbooks/production-runbook-index.md) — All operational runbooks
- [Incident Response](runbooks/incident-response.md) — Incident management procedures
- [Deployment Runbook](runbooks/deployment.md) — Deployment procedures
- [Rollback Runbook](runbooks/rollback.md) — Rollback procedures
- [Platform Outage](runbooks/platform_outage.md) — Platform-wide outage response
- [Safety Incident](runbooks/safety_incident.md) — Safety incident response
- [CI/CD Troubleshooting](runbooks/cicd-troubleshooting.md) — CI/CD pipeline troubleshooting

### Ecosystem & Marketplace
- [ECOSYSTEM.md](ECOSYSTEM.md) — AI ecosystem overview
- [EXTENSION_MARKETPLACE.md](EXTENSION_MARKETPLACE.md) — Extension marketplace guide
- [PACKAGE_REGISTRY.md](PACKAGE_REGISTRY.md) — Package registry documentation
- [PLUGIN_VERIFICATION.md](PLUGIN_VERIFICATION.md) — Plugin verification pipeline
- [ROADMAP_PORTAL.md](ROADMAP_PORTAL.md) — Public roadmap and voting
- [OPENAPI_SPEC.md](OPENAPI_SPEC.md) — OpenAPI specification
- [API_PLAYGROUND.md](API_PLAYGROUND.md) — Interactive API explorer
- [DEVELOPER_PORTAL.md](DEVELOPER_PORTAL.md) — Developer portal guide

### Specialized Guides
- [DATABASE_DESIGN.md](DATABASE_DESIGN.md) — Schema design and migrations
- [DATA_FLOW.md](DATA_FLOW.md) — Data pipeline architecture
- [performance-baseline.md](performance-baseline.md) — Performance benchmarks
- [quantization.md](quantization.md) — Model quantization guide
- [coding_standards.md](coding_standards.md) — Code style guidelines
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — Community code of conduct
- [SECURITY.md](SECURITY.md) — Security policy
- [GLOSSARY.md](GLOSSARY.md) — Terms and definitions
- [changelog.md](changelog.md) — Version history
- [SUPPORT.md](SUPPORT.md) — Support channels
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — Troubleshooting guide
- [migration-guides.md](migration-guides.md) — Migration guides

### Certification & Compliance
- [certification/v1.0.md](certification/v1.0.md) — v1.0 quality certification

## Quick Navigation

| Role | Start Here |
|------|------------|
| New Developer | [QUICK_START.md](QUICK_START.md) → [SETUP.md](SETUP.md) → [CONTRIBUTING.md](CONTRIBUTING.md) |
| Backend Engineer | [API.md](API.md) → [ARCHITECTURE.md](ARCHITECTURE.md) → [DATABASE_DESIGN.md](DATABASE_DESIGN.md) |
| Frontend Engineer | [README.md](../README.md) → [SDK.md](SDK.md) |
| DevOps / SRE | [DEPLOYMENT.md](DEPLOYMENT.md) → [MONITORING.md](MONITORING.md) → [runbooks/](runbooks/) |
| Product Manager | [ROADMAP.md](roadmap.md) → [API.md](API.md) |
| Security Engineer | [SECURITY_BEST_PRACTICES.md](SECURITY_BEST_PRACTICES.md) → [SECURITY_AUDIT.md](SECURITY_AUDIT.md) |
| Extension Developer | [extensions.md](extensions.md) → [PLUGIN_DEVELOPER_GUIDE.md](PLUGIN_DEVELOPER_GUIDE.md) |
| AI Researcher | [inference.md](inference.md) → [training.md](training.md) → [safety.md](safety.md) |

## Documentation Standards

- All public APIs must be documented in [API.md](API.md)
- Architecture decisions are recorded in `docs/adr/`
- Breaking changes follow [api_versioning_policy.md](api_versioning_policy.md)
- Security incidents follow [postmortem_template.md](postmortem_template.md)

## Contributing to Docs

Found a gap or error? Please open an issue or submit a PR following [CONTRIBUTING.md](CONTRIBUTING.md).
