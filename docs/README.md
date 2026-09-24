# AstrovoxAI API Documentation

Quick-reference endpoint table for the AstrovoxAI backend.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | No | Health check |
| `GET` | `/health/readiness` | No | Readiness probe |
| `GET` | `/health/liveness` | No | Liveness probe |
| `POST` | `/auth/signup` | No | Register new user |
| `POST` | `/auth/login` | No | Login and get tokens |
| `POST` | `/auth/logout` | Yes | Logout current session |
| `POST` | `/auth/reset-password` | No | Request password reset |
| `GET` | `/auth/me` | Yes | Get current user profile |
| `POST` | `/chat/conversations` | Yes | Create a conversation |
| `GET` | `/chat/conversations` | Yes | List conversations |
| `GET` | `/chat/conversations/{id}` | Yes | Get conversation details |
| `POST` | `/chat/message` | Yes | Send a message |
| `DELETE` | `/chat/conversations/{id}` | Yes | Delete a conversation |
| `POST` | `/chat/stream` | Yes | Stream a chat response |
| `POST` | `/memory/save` | Yes | Save a memory entry |
| `GET` | `/memory` | Yes | List memory entries |
| `POST` | `/memory/context` | Yes | Get memory context |
| `GET` | `/api/status` | No | API status |
| `GET` | `/api/me` | Yes | Current user info |
| `GET` | `/api/stats` | Yes | User statistics |
| `POST` | `/telemetry/event` | Yes | Track custom event |
| `POST` | `/telemetry/page-view` | Yes | Track page view |
| `POST` | `/telemetry/error` | Yes | Track error |
| `POST` | `/telemetry/user-action` | Yes | Track user action |
| `GET` | `/telemetry/stats` | Yes | Get telemetry stats |
| `GET` | `/metrics` | No | Prometheus metrics |

Base URL: `http://localhost:8000`

All protected endpoints require an `Authorization: Bearer <access_token>` header.
