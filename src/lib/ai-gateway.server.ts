import { createOpenAICompatible } from "@ai-sdk/openai-compatible";

const LOVABLE_AIG_RUN_ID_HEADER = "X-Lovable-AIG-Run-ID";

export const ASTROVOX_MODELS = [
  { id: "gpt-4o-mini", label: "Astro Swift", description: "Fast, balanced default" },
  { id: "gpt-4o", label: "Astro Pro", description: "Best quality + multimodal" },
  { id: "gpt-4.1-mini", label: "Astro 4.1 Mini", description: "Latest small flagship" },
  { id: "gpt-4.1", label: "Astro 4.1", description: "Latest flagship" },
] as const;

export type AstrovoxModelId = (typeof ASTROVOX_MODELS)[number]["id"];

export const DEFAULT_MODEL: AstrovoxModelId = "gpt-4o-mini";

export const ASTROVOX_SYSTEM_PROMPT = `You are AstrovoxAI — a premium, helpful AI assistant created by the AstrovoxAI team.

Voice:
- Clear, concise, and warm. Use markdown when it improves readability.
- For code, use fenced code blocks with the correct language tag.
- When you don't know something, say so briefly and suggest what would help.
- Never claim to be ChatGPT, Claude, Gemini, or any other product. You are AstrovoxAI.`;

export function createOpenAIProvider(apiKey: string) {
  return createOpenAICompatible({
    name: "openai",
    baseURL: "https://api.openai.com/v1",
    headers: {
      Authorization: `Bearer ${apiKey}`,
    },
  });
}

export function createLovableAiGatewayProvider(lovableApiKey: string, initialRunId?: string) {
  let runId = initialRunId?.trim() || undefined;
  let resolveRunId: (value: string | undefined) => void = () => {};
  let runIdResolved = false;
  const runIdReady = new Promise<string | undefined>((resolve) => {
    resolveRunId = resolve;
  });

  const publishRunId = (value?: string) => {
    const nextRunId = value?.trim() || undefined;
    if (!runId && nextRunId) runId = nextRunId;
    if (!runIdResolved) {
      runIdResolved = true;
      resolveRunId(runId);
    }
  };
  if (runId) publishRunId(runId);

  const provider = createOpenAICompatible({
    name: "lovable",
    baseURL: "https://ai.gateway.lovable.dev/v1",
    headers: {
      "Lovable-API-Key": lovableApiKey,
      "X-Lovable-AIG-SDK": "vercel-ai-sdk",
    },
    fetch: async (input, init) => {
      const headers = new Headers(init?.headers);
      if (runId && !headers.has(LOVABLE_AIG_RUN_ID_HEADER)) {
        headers.set(LOVABLE_AIG_RUN_ID_HEADER, runId);
      }
      try {
        const response = await fetch(input, { ...init, headers });
        publishRunId(response.headers.get(LOVABLE_AIG_RUN_ID_HEADER) ?? undefined);
        return response;
      } catch (error) {
        publishRunId(undefined);
        throw error;
      }
    },
  });

  return Object.assign(provider, {
    getRunId: () => runId,
    waitForRunId: () => (runId ? Promise.resolve(runId) : runIdReady),
  });
}

export function getLovableAiGatewayRunId(request: Request) {
  return request.headers.get(LOVABLE_AIG_RUN_ID_HEADER)?.trim() || undefined;
}