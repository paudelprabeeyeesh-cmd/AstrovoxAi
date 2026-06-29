import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { persistLog } from "@/lib/server-logger";

const Body = z.object({
  level: z.enum(["error", "warn", "info"]).optional(),
  message: z.string().min(1).max(2000),
  stack: z.string().max(8000).optional(),
  url: z.string().max(1000).optional(),
  route: z.string().max(500).optional(),
  meta: z.record(z.string(), z.unknown()).optional(),
});

// Public client-error sink. Validates payload, clamps size, never returns data.
export const Route = createFileRoute("/api/log")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        try {
          const raw = await request.text();
          if (raw.length > 16_000) {
            return new Response(null, { status: 413 });
          }
          const parsed = Body.safeParse(JSON.parse(raw));
          if (!parsed.success) {
            return new Response(null, { status: 400 });
          }
          const ua = request.headers.get("user-agent") ?? null;
          await persistLog({
            source: "client",
            level: parsed.data.level ?? "error",
            message: parsed.data.message,
            stack: parsed.data.stack ?? null,
            url: parsed.data.url ?? null,
            route: parsed.data.route ?? null,
            user_agent: ua,
            meta: parsed.data.meta ?? null,
          });
          return new Response(null, { status: 204 });
        } catch {
          return new Response(null, { status: 400 });
        }
      },
    },
  },
});