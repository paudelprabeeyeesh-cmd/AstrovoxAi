import { createOpenAICompatible } from "@ai-sdk/openai-compatible";

const LOVABLE_AIG_RUN_ID_HEADER = "X-Lovable-AIG-Run-ID";

export const ASTROVOX_MODELS = [
  { id: "google/gemini-3-flash-preview", label: "Astro Flash", description: "Fast, balanced default" },
  { id: "google/gemini-2.5-pro", label: "Astro Pro", description: "Best reasoning + multimodal" },
  { id: "openai/gpt-5", label: "Astro GPT-5", description: "OpenAI flagship" },
  { id: "openai/gpt-5-mini", label: "Astro GPT-5 Mini", description: "Lower-cost OpenAI" },
] as const;

export type AstrovoxModelId = (typeof ASTROVOX_MODELS)[number]["id"];

export const DEFAULT_MODEL: AstrovoxModelId = "google/gemini-3-flash-preview";

export const ASTROVOX_SYSTEM_PROMPT = `You are AstrovoxAI — a premium, helpful AI assistant created by the AstrovoxAI team.

Voice:
- Clear, concise, and warm. Use markdown when it improves readability.
- For code, use fenced code blocks with the correct language tag.
- When you don't know something, say so briefly and suggest what would help.
- Never claim to be ChatGPT, Claude, Gemini, or any other product. You are AstrovoxAI.`;

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