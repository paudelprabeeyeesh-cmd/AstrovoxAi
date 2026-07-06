import { describe, it, expect, beforeEach } from "vitest";
import { rateLimit, __resetRateLimit } from "../src/lib/rate-limit";

describe("rateLimit", () => {
  beforeEach(() => __resetRateLimit());

  it("allows requests up to the limit", () => {
    for (let i = 0; i < 3; i++) {
      expect(rateLimit("k", 3, 60_000).ok).toBe(true);
    }
  });

  it("blocks past the limit with retryAfterSec", () => {
    for (let i = 0; i < 3; i++) rateLimit("k", 3, 60_000);
    const r = rateLimit("k", 3, 60_000);
    expect(r.ok).toBe(false);
    expect(r.retryAfterSec).toBeGreaterThan(0);
  });

  it("scopes buckets by key", () => {
    for (let i = 0; i < 3; i++) rateLimit("a", 3, 60_000);
    expect(rateLimit("a", 3, 60_000).ok).toBe(false);
    expect(rateLimit("b", 3, 60_000).ok).toBe(true);
  });
});