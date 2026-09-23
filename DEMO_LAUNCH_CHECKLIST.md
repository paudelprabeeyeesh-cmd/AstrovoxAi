# Astrovox AI — three-day demo launch checklist

This is the shortest path to a credible, repeatable product demonstration. It prioritizes a complete user journey over unfinished breadth.

## The demo story

1. Sign in as a new user.
2. A workspace opens with a conversation ready immediately.
3. Ask a question and show the streamed response.
4. Stop a long response, retry it, and switch conversations.
5. Show Memory and Settings as inspectable workspace surfaces.
6. Open `/docs` and show health/readiness endpoints.
7. Explain that model/tool actions are server-side, authenticated, rate limited, and request-ID traceable.

## Day 1 — reliability and rehearsal

- Copy `.env.example` to a local `.env`; never commit `.env`.
- Rotate any Supabase credentials exposed in screenshots or chat.
- Run `npm ci` and `npm run build` from this directory.
- Run backend tests from `02-Backend` with `pytest`.
- Apply the Supabase schema and migrations, then verify sign-in, automatic conversation creation, message history, memory, and sign-out.

## Day 2 — product polish

- Seed three conversations: “Research brief”, “Build plan”, and “Customer discovery”.
- Prepare one short prompt that produces a useful streamed answer in under 30 seconds, plus a second prompt for retry/stop testing.
- Check desktop and narrow mobile layouts, including loading, empty, offline, and failed-stream states.
- Record a 90-second backup screen capture in case an external provider is unavailable.

## Day 3 — release and evidence

- Push only the nested repository commit and its parent pointer; confirm GitHub Actions checks are green.
- Tag the demo commit and record its hash in presentation notes.
- Confirm no `.env`, access token, service-role key, or local database is tracked.
- Prepare a one-page results sheet with build status, test count, response latency, and the next three roadmap milestones.

## Do not claim yet

Present voice, vision, autonomous deployment, medical/legal advice, enterprise SSO, and unrestricted code execution as roadmap work until their security, permissions, monitoring, and test gates are complete.
