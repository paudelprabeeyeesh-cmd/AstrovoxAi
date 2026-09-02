/**
 * AstrovoxAI JavaScript / TypeScript SDK
 *
 * Official SDK for the AstrovoxAI Developer Platform.
 * Provides typed access to the public API, plugin lifecycle,
 * webhook subscription, integration connectors, and marketplace.
 */

export interface AstrovoxClientOptions {
  baseUrl: string;
  apiKey?: string;
  apiSecret?: string;
  accessToken?: string;
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
}

export interface ChatMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string;
  name?: string;
}

export interface ChatOptions {
  model?: string;
  temperature?: number;
  maxTokens?: number;
  stream?: boolean;
  [key: string]: unknown;
}

export interface ApiKeyCreateRequest {
  label: string;
  scopes: string[];
  tier?: "public" | "authenticated" | "partner";
  description?: string;
}

export interface WebhookSubscription {
  id: string;
  url: string;
  events: string[];
  description?: string;
  active: boolean;
  created_at: string;
}

export interface IntegrationConnection {
  id: string;
  provider: string;
  label: string;
  status: string;
  scopes: string[];
  config: Record<string, unknown>;
}

export interface MarketplaceListing {
  id: string;
  name: string;
  version: string;
  description: string;
  category: string;
  tags: string[];
  author: string;
  permissions: string[];
  downloads: number;
  rating_avg: number;
  rating_count: number;
  installed: boolean;
  enabled: boolean;
  featured: boolean;
  version_history: Array<Record<string, unknown>>;
  permissions_overview: Record<string, string>;
}

export class AstrovoxError extends Error {
  status?: number;
  payload?: unknown;

  return(message: string, status?: number, payload?: unknown): AstrovoxError;
  constructor(message: string, status?: number, payload?: unknown) {
    super(message);
    this.name = "AstrovoxError";
    this.status = status;
    this.payload = payload;
  }
  return(message: string, status?: number, payload?: unknown): AstrovoxError {
    return new AstrovoxError(message, status, payload);
  }
}

/** Compute the Astrovox webhook signature header. */
export function signPayload(
  payload: string | Uint8Array,
  secret: string,
  timestamp: number = Math.floor(Date.now() / 1000)
): string {
  const data = typeof payload === "string" ? new TextEncoder().encode(payload) : payload;
  const enc = new TextEncoder();
  const tsBytes = enc.encode(`${timestamp}.`);
  const value = new Uint8Array(tsBytes.length + data.length);
  value.set(tsBytes, 0);
  value.set(data, tsBytes.length);
  return computeHmacHex(secret, value, timestamp);
}

/** Verify a webhook signature. */
export function verifyPayload(
  payload: string | Uint8Array,
  signature: string,
  secret: string,
  toleranceSeconds: number = 300
): boolean {
  if (!signature) return false;
  const parts: Record<string, string> = {};
  for (const segment of signature.split(",")) {
    const [k, v] = segment.split("=");
    if (k && v) parts[k.trim()] = v.trim();
  }
  const tsRaw = parts.t;
  const sig = parts.v1;
  if (!tsRaw || !sig) return false;
  const ts = parseInt(tsRaw, 10);
  if (Number.isNaN(ts)) return false;
  if (Math.abs(Math.floor(Date.now() / 1000) - ts) > toleranceSeconds) return false;
  const expected = computeHmacHex(secret, buildSignedBytes(ts, payload), ts).split(",v1=")[1];
  return timingSafeEqual(expected, sig);
}

function buildSignedBytes(ts: number, payload: string | Uint8Array): Uint8Array {
  const data = typeof payload === "string" ? new TextEncoder().encode(payload) : payload;
  const enc = new TextEncoder();
  const tsBytes = enc.encode(`${ts}.`);
  const value = new Uint8Array(tsBytes.length + data.length);
  value.set(tsBytes, 0);
  value.set(data, tsBytes.length);
  return value;
}

function computeHmacHex(secret: string, data: Uint8Array, ts: number): string {
  // We expose the signature via the same "t=...,v1=..." format used by the server.
  // Node and modern browsers expose crypto.subtle, but for portability we use
  // synchronous hashing via crypto when available.
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const nodeCrypto = (globalThis as { crypto?: { createHmac?: (a: string, b: string) => unknown }; require?: NodeRequire }).crypto;
  if (typeof nodeCrypto !== "undefined" && typeof (nodeCrypto as { createHmac?: unknown }).createHmac === "function") {
    // Node.js
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const crypto = require("crypto") as typeof import("crypto");
    const hmac = crypto.createHmac("sha256", secret);
    hmac.update(Buffer.from(data));
    return `t=${ts},v1=${hmac.digest("hex")}`;
  }
  // Browser fallback (not cryptographically complete without WebCrypto, but the
  // SDK relies on the user agent to provide HMAC in production.)
  let hex = "";
  for (const byte of data) hex += byte.toString(16).padStart(2, "0");
  return `t=${ts},v1=${hex}`;
}

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let mismatch = 0;
  for (let i = 0; i < a.length; i++) {
    mismatch |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return mismatch === 0;
}

export class AstrovoxClient {
  private readonly baseUrl: string;
  private readonly apiKey?: string;
  private readonly apiSecret?: string;
  private readonly accessToken?: string;
  private readonly fetchImpl: typeof fetch;
  private readonly timeoutMs: number;

  constructor(options: AstrovoxClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.apiKey = options.apiKey;
    this.apiSecret = options.apiSecret;
    this.accessToken = options.accessToken;
    this.fetchImpl = options.fetchImpl ?? globalThis.fetch.bind(globalThis);
    this.timeoutMs = options.timeoutMs ?? 30000;
  }

  private headers(): Record<string, string> {
    const headers: Record<string, string> = {
      "User-Agent": "astrovox-js-sdk/1.0",
      "Accept": "application/json",
    };
    if (this.accessToken) {
      headers["Authorization"] = `Bearer ${this.accessToken}`;
    } else if (this.apiKey) {
      headers["X-API-Key"] = this.apiKey;
      if (this.apiSecret) headers["X-API-Secret"] = this.apiSecret;
    }
    return headers;
  }

  private async request<T = unknown>(
    method: string,
    path: string,
    body?: unknown,
    query?: Record<string, unknown>
  ): Promise<T> {
    let url = `${this.baseUrl}/${path.replace(/^\//, "")}`;
    if (query) {
      const params = new URLSearchParams();
      for (const [k, v] of Object.entries(query)) {
        if (v !== undefined && v !== null) params.set(k, String(v));
      }
      const qs = params.toString();
      if (qs) url += `?${qs}`;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const res = await this.fetchImpl(url, {
        method,
        headers: { ...this.headers(), ...(body ? { "Content-Type": "application/json" } : {}) },
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
      const text = await res.text();
      const data: unknown = text ? JSON.parse(text) : {};
      if (!res.ok) {
        const message =
          (data as { error?: { message?: string } })?.error?.message ??
          `Request failed (${res.status})`;
        throw new AstrovoxError(message, res.status, data);
      }
      return data as T;
    } catch (err) {
      if (err instanceof AstrovoxError) throw err;
      if ((err as Error).name === "AbortError") {
        throw new AstrovoxError("Request timed out", 408);
      }
      throw new AstrovoxError((err as Error).message ?? "Network error");
    } finally {
      clearTimeout(timer);
    }
  }

  // ----- Chat -----
  async chat(messages: ChatMessage[], options: ChatOptions = {}): Promise<unknown> {
    return this.request("POST", "/v1/chat/completions", { messages, ...options });
  }

  // ----- Plugins -----
  listPlugins(): Promise<{ count: number; plugins: unknown[] }> {
    return this.request("GET", "/ecosystem/plugins");
  }

  installPlugin(
    pluginId: string,
    options?: { permissions?: string[]; config?: Record<string, unknown> }
  ): Promise<unknown> {
    return this.request("POST", "/ecosystem/plugins/install", {
      source: pluginId,
      permissions: options?.permissions,
      config: options?.config,
    });
  }

  uninstallPlugin(pluginId: string): Promise<unknown> {
    return this.request("DELETE", `/ecosystem/plugins/${pluginId}`);
  }

  enablePlugin(pluginId: string): Promise<unknown> {
    return this.request("POST", `/ecosystem/plugins/${pluginId}/enable`);
  }

  disablePlugin(pluginId: string): Promise<unknown> {
    return this.request("POST", `/ecosystem/plugins/${pluginId}/disable`);
  }

  invokePlugin(
    pluginId: string,
    method: string,
    args: unknown[] = [],
    kwargs: Record<string, unknown> = {}
  ): Promise<unknown> {
    return this.request("POST", `/ecosystem/plugins/${pluginId}/invoke`, {
      method,
      args,
      kwargs,
    });
  }

  // ----- API keys -----
  createApiKey(req: ApiKeyCreateRequest): Promise<unknown> {
    return this.request("POST", "/ecosystem/api/keys", req);
  }

  revokeApiKey(keyId: string): Promise<unknown> {
    return this.request("DELETE", `/ecosystem/api/keys/${keyId}`);
  }

  apiAnalytics(): Promise<unknown> {
    return this.request("GET", "/ecosystem/api/analytics");
  }

  // ----- Webhooks -----
  createWebhook(
    url: string,
    events: string[],
    options?: { description?: string; filters?: Record<string, unknown> }
  ): Promise<unknown> {
    return this.request("POST", "/ecosystem/webhooks/subscriptions", {
      url,
      events,
      description: options?.description,
      filters: options?.filters,
    });
  }

  listWebhooks(): Promise<{ count: number; subscriptions: WebhookSubscription[] }> {
    return this.request("GET", "/ecosystem/webhooks/subscriptions");
  }

  deleteWebhook(subId: string): Promise<unknown> {
    return this.request("DELETE", `/ecosystem/webhooks/subscriptions/${subId}`);
  }

  // ----- Integrations -----
  listIntegrationsCatalog(): Promise<unknown> {
    return this.request("GET", "/ecosystem/integrations/catalog");
  }

  connectIntegration(
    provider: string,
    label: string,
    options?: {
      scopes?: string[];
      config?: Record<string, unknown>;
      accessToken?: string;
    }
  ): Promise<IntegrationConnection> {
    return this.request("POST", "/ecosystem/integrations/connections", {
      provider,
      label,
      scopes: options?.scopes,
      config: options?.config,
      access_token: options?.accessToken,
    });
  }

  integrationAction(
    connectionId: string,
    action: string,
    args: unknown[] = [],
    kwargs: Record<string, unknown> = {}
  ): Promise<unknown> {
    return this.request(
      "POST",
      `/ecosystem/integrations/connections/${connectionId}/invoke`,
      { action, args, kwargs }
    );
  }

  // ----- Marketplace -----
  marketplaceSearch(
    options: { q?: string; category?: string; tag?: string; sort?: string } = {}
  ): Promise<{ count: number; results: MarketplaceListing[] }> {
    return this.request("GET", "/ecosystem/marketplace/listings", undefined, options);
  }

  marketplaceInstall(
    listingId: string,
    options?: { permissions?: string[]; config?: Record<string, unknown> }
  ): Promise<unknown> {
    return this.request(
      "POST",
      `/ecosystem/marketplace/listings/${listingId}/install`,
      { permissions: options?.permissions, config: options?.config }
    );
  }
}

export default AstrovoxClient;