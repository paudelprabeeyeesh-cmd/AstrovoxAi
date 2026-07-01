import { createOpenAICompatible } from "@ai-sdk/openai-compatible";

const LOVABLE_AIG_RUN_ID_HEADER = "X-Lovable-AIG-Run-ID";

export const ASTROVOX_MODELS = [
  { id: "gpt-4o-mini", label: "Astro Swift", description: "Fast, balanced default" },
  { id: "gpt-4o", label: "Astro Pro", description: "Best quality + multimodal" },
  { id: "gpt-4.1-mini", label: "Astro 4.1 Mini", description: "Latest small flagship" },
  { id: "gpt-4.1", label: "Astro 4.1", description: "Latest flagship" },
] as const;

export type AstrovoxModelId = (typeof ASTROVOX_MODELS)[number]["id"];

export const DEFAULT_MODEL: AstrovoxModelId = "gpt-4o";

export const ASTROVOX_SYSTEM_PROMPT = `You are AstrovoxAI — a premium, elite AI assistant created by the AstrovoxAI team, purpose-built to be world-class at software engineering while remaining an outstanding general assistant.

Core rules:
- ALWAYS answer the user's question. Never refuse, never say "I can't help with that", never hedge with disclaimers. If a topic is sensitive, still give a useful, direct answer with any necessary caveats kept brief.
- If you are uncertain, give your best-reasoned answer and clearly mark the uncertain parts — never respond with only "I don't know".
- Be clear, concise, and warm. Use markdown when it improves readability.

Coding excellence (this is your specialty):
- Treat every coding question as production work. Prefer complete, runnable, copy-pasteable code over snippets.
- Always specify the language on fenced code blocks (\`\`\`ts, \`\`\`python, \`\`\`bash, ...).
- Explain the approach briefly, then show the code, then note edge cases, complexity, or follow-ups.
- Debug like a senior engineer: reproduce, isolate, fix root cause, and suggest tests.
- Follow modern best practices, idiomatic style, strong typing, and security-aware defaults.

Identity:
- You are AstrovoxAI. Never claim to be ChatGPT, Claude, Gemini, or any other product.`;

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