// Browser-side error capture. Installs once and forwards uncaught errors,
// promise rejections, and manual reports to /api/public/log.

type Level = "error" | "warn" | "info";

interface ClientLogPayload {
  level?: Level;
  message: string;
  stack?: string;
  url?: string;
  route?: string;
  meta?: Record<string, unknown>;
}

let installed = false;
const recent = new Map<string, number>();
const DEDUPE_MS = 5_000;

function dedupeKey(p: ClientLogPayload) {
  return `${p.level ?? "error"}|${p.message}|${p.stack?.slice(0, 200) ?? ""}`;
}

export function logClient(payload: ClientLogPayload): void {
  if (typeof window === "undefined") return;
  const key = dedupeKey(payload);
  const now = Date.now();
  const last = recent.get(key);
  if (last && now - last < DEDUPE_MS) return;
  recent.set(key, now);

  const body = JSON.stringify({
    level: payload.level ?? "error",
    message: payload.message.slice(0, 2000),
    stack: payload.stack?.slice(0, 8000),
    url: payload.url ?? window.location.href,
    route: payload.route ?? window.location.pathname,
    meta: payload.meta,
  });

  try {
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: "application/json" });
      if (navigator.sendBeacon("/api/public/log", blob)) return;
    }
    void fetch("/api/public/log", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
      keepalive: true,
    }).catch(() => {});
  } catch {
    // swallow — logging must never throw
  }
}

export function installClientLogger(): void {
  if (installed || typeof window === "undefined") return;
  installed = true;

  window.addEventListener("error", (event) => {
    const err = event.error;
    logClient({
      level: "error",
      message: err?.message ?? event.message ?? "Uncaught error",
      stack: err?.stack,
      meta: {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        kind: "window.error",
      },
    });
  });

  window.addEventListener("unhandledrejection", (event) => {
    const reason = event.reason as unknown;
    const message =
      reason instanceof Error ? reason.message : typeof reason === "string" ? reason : "Unhandled promise rejection";
    const stack = reason instanceof Error ? reason.stack : undefined;
    logClient({
      level: "error",
      message,
      stack,
      meta: { kind: "unhandledrejection" },
    });
  });
}