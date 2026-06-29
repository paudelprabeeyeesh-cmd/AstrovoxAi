// Server-only logging helper. Persists structured logs to public.error_logs
// via the service role (bypasses RLS). Safe to call from server functions,
// server routes, and request middleware.

export type LogLevel = "error" | "warn" | "info";
export type LogSource = "server" | "client";

export interface LogRecord {
  source: LogSource;
  level?: LogLevel;
  message: string;
  stack?: string | null;
  url?: string | null;
  route?: string | null;
  method?: string | null;
  status?: number | null;
  duration_ms?: number | null;
  user_id?: string | null;
  user_agent?: string | null;
  meta?: Record<string, unknown> | null;
}

const MAX_MSG = 2000;
const MAX_STACK = 8000;

function clamp(value: string | null | undefined, max: number): string | null {
  if (!value) return null;
  return value.length > max ? value.slice(0, max) : value;
}

export async function persistLog(record: LogRecord): Promise<void> {
  try {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const row = {
      source: record.source,
      level: record.level ?? "error",
      message: clamp(record.message, MAX_MSG) ?? "(empty)",
      stack: clamp(record.stack ?? null, MAX_STACK),
      url: clamp(record.url ?? null, 1000),
      route: clamp(record.route ?? null, 500),
      method: record.method ?? null,
      status: record.status ?? null,
      duration_ms: record.duration_ms ?? null,
      user_id: record.user_id ?? null,
      user_agent: clamp(record.user_agent ?? null, 500),
      meta: (record.meta ?? null) as never,
    };
    const { error } = await supabaseAdmin.from("error_logs").insert(row);
    if (error) console.error("[server-logger] persist failed:", error.message);
  } catch (err) {
    // Never let logging crash the request.
    console.error("[server-logger] unexpected:", err);
  }
}

export function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  try { return JSON.stringify(error); } catch { return String(error); }
}

export function errorStack(error: unknown): string | null {
  return error instanceof Error && error.stack ? error.stack : null;
}