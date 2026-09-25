# AstrovoxAI — AI Platform Architecture

## System Overview

AstrovoxAI is an enterprise-grade AI platform with multi-agent collaboration, workflow automation, and comprehensive tool execution capabilities.

```
┌─────────────────────────────────────────────────────────────┐
│                      CLIENT LAYER                            │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────────┐    │
│  │  Web App │  │ Mobile   │  │  API Clients           │    │
│  └────┬─────┘  └────┬─────┘  └──────────┬─────────────┘    │
│       └──────────────┼──────────────────┘                   │
└──────────────────────┼──────────────────────────────────────┘
                       │
┌──────────────────────┼──────────────────────────────────────┐
│                 API GATEWAY                                   │
│  ┌──────────┐  ┌─────┴─────┐  ┌──────────────────────┐     │
│  │ Auth     │  │ Rate      │  │  Request Validation  │     │
│  │ Middleware│  │ Limiter   │  │  & Sanitization     │     │
│  └──────────┘  └───────────┘  └──────────────────────┘     │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┼──────────────────────────────────────┐
│                   SERVICE LAYER                               │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                Agent Framework                       │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │    │
│  │  │ Planner  │  │ Researcher│  │  Coder           │  │    │
│  │  └──────────┘  └──────────┘  └──────────────────┘  │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │    │
│  │  │ Reviewer │  │ Security │  │  Orchestrator    │  │    │
│  │  └──────────┘  └──────────┘  └──────────────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Specialized Agents                      │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │    │
│  │  │ Memory   │  │ File     │  │  Testing         │  │    │
│  │  └──────────┘  └──────────┘  └──────────────────┘  │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │    │
│  │  │ Debugging│  │ Report   │  │  Documentation   │  │    │
│  │  └──────────┘  └──────────┘  └──────────────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Workflow   │  │    Tool      │  │    Shared        │  │
│  │   Engine     │  │  Execution   │  │    Memory        │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Dashboard   │  │  Analytics   │  │  Performance     │  │
│  │  Service     │  │  Collector   │  │  Monitor         │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                       │
┌──────────────────────┼──────────────────────────────────────┐
│                    DATA LAYER                                 │
│  ┌──────────┐  ┌─────┴─────┐  ┌──────────────────────┐     │
│  │ Supabase │  │  Redis    │  │  Local Storage       │     │
│  │ (Auth +  │  │  (Cache)  │  │  (Files)            │     │
│  │  DB)     │  │           │  │                      │     │
│  └──────────┘  └───────────┘  └──────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

## Core Components

### Agent Framework
- **Lifecycle Management**: CREATED → INITIALIZING → READY → RUNNING → WAITING → COMPLETED → FAILED → RECOVERING → STOPPED
- **Registry**: Dynamic agent registration with health monitoring
- **Orchestrator**: Task decomposition, agent selection, parallel execution
- **Collaboration**: Multi-agent sessions with shared context

### Workflow Engine
- **Steps**: AGENT_TASK, WEBHOOK, DELAY, APPROVED, CONDITION, LOOP
- **Execution**: Sequential, parallel, or adaptive modes
- **Templates**: Reusable workflow templates with cloning
- **Retry**: Exponential backoff with configurable limits

### Tool Execution
- **Security**: Permission checks, rate limiting, sandboxing
- **Audit**: Full execution logging for compliance
- **Metrics**: Performance tracking and analytics

## API Reference

### Authentication
All endpoints require Bearer token: `Authorization: Bearer <token>`

### Agent Management
- `GET /api/v1/agents` - List all agents
- `GET /api/v1/agents/{role}` - Get agent details
- `GET /api/v1/agents/{role}/health` - Get agent health

### Workflow Management
- `POST /api/v1/workflows` - Create workflow
- `GET /api/v1/workflows` - List workflows
- `GET /api/v1/workflows/{id}` - Get workflow details
- `POST /api/v1/workflows/{id}/execute` - Execute workflow
- `GET /api/v1/workflows/templates` - List templates
- `POST /api/v1/workflows/templates` - Create template

### Tool Execution
- `GET /api/v1/tools` - List available tools
- `POST /api/v1/tools/{name}/execute` - Execute a tool

### Collaboration
- `POST /api/v1/collaborations?goal=<goal>` - Create collaboration session
- `GET /api/v1/collaborations` - List sessions
- `GET /api/v1/collaborations/{id}` - Get session details
- `POST /api/v1/collaborations/{id}/run` - Run session

### Dashboard
- `GET /api/dashboard/stats` - Platform statistics
- `GET /api/dashboard/tasks` - Running tasks
- `GET /api/dashboard/workflows` - Workflow status
- `GET /api/dashboard/agents` - Agent information
- `GET /api/dashboard/tools` - Tool registry
- `GET /api/dashboard/logs` - Agent logs
- `GET /api/dashboard/timeline` - Execution timeline
- `GET /api/dashboard/metrics` - Tool metrics

## Security Architecture

### Authentication
- JWT-based authentication via Supabase
- Token validation on every request
- Session management with refresh tokens

### Authorization
- Role-based access control (User < Developer < Admin)
- Permission checks on all endpoints
- Resource ownership validation

### Rate Limiting
- Per-IP rate limiting via slowapi
- Per-user rate limiting on tool execution
- Configurable limits per endpoint

### Tool Security
- Permission checks before execution
- Resource limits (time, memory, output size)
- Dangerous pattern blocking in code execution
- Full audit logging

## Deployment

### Docker
```bash
docker-compose up --dockerfile Dockerfile.backend
```

### Kubernetes
See `kubernetes/` directory for manifests.

## Testing
```bash
cd 02-Backend
pytest
```

All 406 tests must pass before deployment.
