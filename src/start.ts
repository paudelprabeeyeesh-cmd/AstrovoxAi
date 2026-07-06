import { createStart, createMiddleware } from "@tanstack/react-start";

import { renderErrorPage } from "./lib/error-page";
import { attachSupabaseAuth } from "@/integrations/supabase/auth-attacher";
import { persistLog, errorMessage, errorStack } from "./lib/server-logger";

function safePathname(url: string): string {
  try {
    return new URL(url).pathname;
  } catch {
    return url;
  }
}

const errorMiddleware = createMiddleware().server(async ({ next, request }) => {
  const started = Date.now();
  const method = request.method;
  const route = safePathname(request.url);
  try {
    const response = await next();
    applySecurityHeaders(response as unknown as Response | undefined);
    const duration = Date.now() - started;
    // Log slow or 5xx responses for visibility.
    const maybeResponse = response as unknown as { status?: number } | undefined;
    const status = maybeResponse?.status;
    if (status && status >= 500) {
      void persistLog({
        source: "server",
        level: "error",
        message: `Server responded ${status} for ${method} ${route}`,
        method,
        route,
        status,
        duration_ms: duration,
        url: request.url,
      });
    }
    return response;
  } catch (error) {
    if (error != null && typeof error === "object" && "statusCode" in error) {
      throw error;
    }
    const message = error instanceof Error ? error.message : String(error);
    if (message.startsWith("Unauthorized")) {
      return new Response(JSON.stringify({ error: message }), {
        status: 401,
        headers: { "content-type": "application/json" },
      });
    }
    console.error(error);
    void persistLog({
      source: "server",
      level: "error",
      message: errorMessage(error),
      stack: errorStack(error),
      method,
      route,
      status: 500,
      duration_ms: Date.now() - started,
      url: request.url,
      user_agent: request.headers.get("user-agent"),
    });
    const errResp = new Response(renderErrorPage(), {
      status: 500,
      headers: { "content-type": "text/html; charset=utf-8" },
    });
    applySecurityHeaders(errResp);
    return errResp;
  }
});

function applySecurityHeaders(response: Response | undefined) {
  if (!response || !response.headers) return;
  const h = response.headers;
  // Baseline headers; safe defaults that don't interfere with the app.
  if (!h.has("x-content-type-options")) h.set("x-content-type-options", "nosniff");
  if (!h.has("referrer-policy")) h.set("referrer-policy", "strict-origin-when-cross-origin");
  if (!h.has("x-frame-options")) h.set("x-frame-options", "SAMEORIGIN");
  if (!h.has("permissions-policy"))
    h.set("permissions-policy", "camera=(), microphone=(), geolocation=()");
  if (!h.has("strict-transport-security"))
    h.set("strict-transport-security", "max-age=31536000; includeSubDomains");
}

export const startInstance = createStart(() => ({
  functionMiddleware: [attachSupabaseAuth],
  requestMiddleware: [errorMiddleware],
}));
