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