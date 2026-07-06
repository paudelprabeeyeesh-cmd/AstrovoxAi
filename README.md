<<<<<<< HEAD
# ASTRAVOX PRIME

## Advanced AI Chat Platform

ASTRAVOX PRIME is a cutting-edge AI chat platform designed to provide an intelligent and interactive conversational experience. It features a modern React frontend, a robust FastAPI backend, and leverages Supabase for its database and authentication needs. The platform is built with scalability and maintainability in mind, ensuring a seamless experience for users and developers alike.

## Features

- **User Authentication**: Secure sign-up, login, logout, and password reset functionalities powered by Supabase Auth.
- **Persistent Sessions**: Users remain logged in across sessions, providing a continuous experience.
- **Protected Routes**: Ensures that only authenticated users can access sensitive parts of the application.
- **AI Chat Interface**: A dynamic chat environment where users can interact with an AI, create new conversations, and review past interactions.
- **Conversation History**: All messages and conversations are saved and can be loaded for future reference.
- **AI Memory System**: An intelligent memory system that stores important information from conversations, allowing the AI to provide more personalized and context-aware responses.
- **Dashboard**: A comprehensive dashboard featuring:
    - **Sidebar**: For managing and navigating between conversations.
    - **Telemetry**: Real-time system diagnostics and statistics.
    - **Terminal Console**: An interactive command-line interface for system interactions.
    - **Memory Panel**: To view and manage AI memory entries.
    - **Settings Panel**: For user-specific configurations, including AI model preferences and theme settings.
- **Responsive UI**: Designed to provide an optimal viewing and interaction experience across a wide range of devices.
- **Modular Backend**: A FastAPI backend with a clear, modular architecture for easy development and maintenance.
- **Supabase Integration**: Utilizes Supabase for PostgreSQL database, authentication, and real-time capabilities.

## Technology Stack

- **Frontend**: React, Vite, TailwindCSS
- **Backend**: FastAPI, Python
- **Database**: Supabase (PostgreSQL)
- **Authentication**: Supabase Auth
- **AI Integration**: OpenAI API

## Getting Started

To set up and run ASTRAVOX PRIME locally, please refer to the [SETUP.md](SETUP.md) guide.

### Production-ready capabilities added
- Persistent usage quotas backed by SQLite instead of process-local memory.
- HTTP rate limiting middleware with per-request headers.
- Storage endpoints for upload/delete/signed URL generation with ownership checks.
- Backend validation for chat payloads and supported AI models.
- Expanded automated tests for usage, storage, auth, and health routes.

### Verification
- Backend tests: `c:/AstrovoxAi/venv/Scripts/python.exe -m pytest -q`
- Frontend build: `npm run build`

### Deployment checklist
1. Configure Supabase URL and anon key.
2. Configure OpenAI API key.
3. Set ALLOWED_ORIGINS for the deployed frontend domain.
4. Set RATE_LIMIT and DAILY_AI_LIMIT to desired production values.
5. Apply the SQL schema and RLS policies in Supabase.
6. Ensure the storage root is writable in the deployment environment.

## API Documentation

For detailed information on the available API endpoints, request/response formats, and authentication mechanisms, please consult the [API.md](API.md) documentation.

## Project Structure

```
AstrovoxAi/
├── src/                    # React frontend components and logic
├── 02-Backend/            # FastAPI backend application
│   ├── app/                # FastAPI application modules (auth, chat, api, memory, database)
│   └── requirements.txt    # Python dependencies
├── database/               # Database schema and migration scripts
│   └── schemas/
├── .env                    # Environment variables (local configuration)
├── .env.example            # Example environment variables
├── package.json            # Frontend dependencies and scripts
├── vite.config.js          # Vite build configuration
├── index.html              # Frontend HTML entry point
├── README.md               # Project overview
├── SETUP.md                # Setup and installation guide
├── API.md                  # API documentation
└── ROADMAP.md              # Future development roadmap
```

## Contributing

We welcome contributions to ASTRAVOX PRIME! Please refer to the [ROADMAP.md](ROADMAP.md) for planned features and consider opening an issue or pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License.

## Authors
Prabesh Paudel

    Founder & Chief Executive Officer (CEO)

    Chief AI Architect

    Principal Software Engineer

    Lead Full-Stack Engineer

    Software Solutions Architect

    AI Systems Designer

    DevOps Engineer

    Product Strategist

    Technical Lead

Dipson Baral

    Co-Founder

    Senior Full-Stack Software Engineer

    Backend Engineer

    DevOps Engineer

    API & Database Engineer

Susanta Baral

    AI Research Engineer

    Machine Learning Engineer

    Data & AI Engineer

    AI Model Integration Engineer

    Prompt Engineering Specialist

=======
# AstrovoxAI

Premium AI chat app built on TanStack Start (React 19, Vite 7) with a
Supabase-backed Lovable Cloud backend. Chat streams responses from the
Lovable AI Gateway (Gemini + GPT models), renders Markdown with KaTeX
math and Mermaid diagrams, and persists conversations per user.

## Stack

- **Frontend:** React 19, TanStack Router/Start, Tailwind v4, shadcn/ui
- **Backend:** TanStack server functions + server routes (Cloudflare Worker runtime)
- **Data + Auth:** Lovable Cloud (Supabase) with Row Level Security
- **AI:** Lovable AI Gateway (`google/gemini-3-flash-preview`, `google/gemini-2.5-pro`, `openai/gpt-5-mini`, `openai/gpt-5`) via `ai` SDK streaming
- **Rendering:** `react-markdown`, `remark-gfm`, `remark-math`, `rehype-katex`, Mermaid

## Scripts

| Command | Purpose |
| --- | --- |
| `bun run dev` | Start Vite dev server |
| `bun run build` | Production build |
| `bun run build:dev` | Preview/prerender build |
| `bun run test` | Run unit tests (Vitest) |
| `bun run lint` | ESLint |
| `bun run format` | Prettier |

## Project layout

```
src/
  components/chat/        Chat UI (window, sidebar, markdown, mermaid)
  integrations/supabase/  Auto-generated Supabase clients + middleware
  lib/                    Server helpers, ai-gateway, rate-limit, logger
  routes/                 File-based routes
    api/chat.ts           Streaming chat endpoint (auth + rate limited)
    api/public/log.ts     Client error sink
    _authenticated/       Signed-in surfaces (chat, settings)
    auth.tsx              Sign in / sign up
    about.tsx, index.tsx  Public marketing pages
tests/                    Vitest unit tests
```

## Auth

Email/password + Google OAuth via Lovable Cloud. Protected routes live
under `src/routes/_authenticated/` and are gated by the integration-managed
`_authenticated/route.tsx` layout. Server functions that need the current
user use `requireSupabaseAuth`; the bearer token is attached automatically
by `attachSupabaseAuth` in `src/start.ts`.

## Data model

- `profiles` — one row per auth user (auto-populated by `handle_new_user`)
- `conversations` — per-user chat threads (title, model, timestamps)
- `messages` — user/assistant messages linked to a conversation
- `error_logs` — server + client error sink (service-role writes only)

All user-owned tables have RLS scoped to `auth.uid()`.

## Security

- Every server route validates input with Zod and clamps message/body size.
- `/api/chat` enforces a per-user ad-hoc rate limit (30 req/min, in-memory).
- Response middleware sets `X-Content-Type-Options`, `Referrer-Policy`,
  `X-Frame-Options`, `Permissions-Policy`, and HSTS.
- Markdown rendering uses `securityLevel: "strict"` for Mermaid and never
  injects raw HTML from user messages.
- Service-role key is loaded only inside server handlers, never at module scope.

## Testing

Run `bun run test`. Vitest config lives in `vitest.config.ts` and tests in
`tests/`. Current coverage focuses on pure server helpers
(`rate-limit`, `ai-gateway`); expand with route-level tests as the surface grows.

## Deployment

Publish from the Lovable editor (Publish button). Frontend changes require
"Update" in the publish dialog; server function / route changes deploy
automatically. Stable URLs:

- Production: `project--<project-id>.lovable.app`
- Preview: `project--<project-id>-dev.lovable.app`

Custom domains are configured in Project settings → Domains.

## Environment

Runtime secrets (managed via Lovable Cloud):

- `LOVABLE_API_KEY` — AI Gateway + connectors (auto-provisioned)
- `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`

Client-visible (`.env`, safe to commit): `VITE_SUPABASE_URL`,
`VITE_SUPABASE_PUBLISHABLE_KEY`, `VITE_SUPABASE_PROJECT_ID`.
>>>>>>> source/main
