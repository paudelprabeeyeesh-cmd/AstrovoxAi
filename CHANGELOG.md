# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 1 production hardening: load testing, chaos testing, security audit, incident runbook
- Phase 2 engineering excellence: ADRs, coding standards, contribution guide, release strategy
- Phase 3-7 artifacts: benchmarking lab, AI research modules, SRE tooling, enterprise features, open source scaffolding

### Changed
- Removed duplicate unauthenticated `/metrics` endpoint
- Restricted `execute_bash` to allowlist with `shell=False`
- Made `ASTROVOX_ENCRYPTION_KEY` required at boot
- Fixed frontend chat proxy to use `NEXT_PUBLIC_API_URL`
- Replaced global `PII_STORE` with per-request contextvar
- Fixed rate-limit bypass via explicit 401 returns

### Fixed
- Frontend `Authorization` header malformed on sign-out
- `/health/detailed` now requires admin authentication

## [1.0.0] - 2026-09-17

### Added
- Initial production release
- FastAPI backend with 120+ endpoints
- Next.js 16 frontend with 23 pages
- Multi-provider LLM routing (7 providers)
- RAG engine with PDF/DOCX/TXT support
- GraphRAG with Neo4j
- Agent system with 6 specialized agents
- WebSocket streaming
- Voice I/O, vision, OCR, code execution
- Kubernetes deployment manifests
- CI/CD pipeline with security scanning
- SOC 2 compliance documentation
