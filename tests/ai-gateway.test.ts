import { describe, it, expect } from "vitest";
import { normalizeModelId, DEFAULT_MODEL, ASTROVOX_MODELS } from "../src/lib/ai-gateway.server";

describe("normalizeModelId", () => {
  it("returns the default for unknown ids", () => {
    expect(normalizeModelId("gpt-4o-mini")).toBe(DEFAULT_MODEL);
    expect(normalizeModelId(null)).toBe(DEFAULT_MODEL);
    expect(normalizeModelId(undefined)).toBe(DEFAULT_MODEL);
  });

  it("passes through allowed model ids", () => {
    for (const m of ASTROVOX_MODELS) {
      expect(normalizeModelId(m.id)).toBe(m.id);
    }
  });
});