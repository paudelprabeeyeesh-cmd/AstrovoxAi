import type { IEmbedder } from '../contracts/IEmbedder';

const OPENAI_EMBED_ENDPOINT = 'https://api.openai.com/v1/embeddings';

export class OpenAIEmbedder implements IEmbedder {
  name = 'openai-embedder';
  private apiKey: string | undefined;
  private dimension?: number;

  constructor() {
    this.apiKey = process.env.OPENAI_API_KEY;
  }

  async init(): Promise<void> {
    if (!this.apiKey) return; // mock-mode
    // optional: probe model to determine dimension; skip for now
  }

  getDimension(): number | undefined { return this.dimension; }

  async embed(inputs: string[], options?: { namespace?: string; model?: string; signal?: AbortSignal }): Promise<number[][]> {
    if (!this.apiKey) {
      // mock embeddings (deterministic hash-based) for offline/test mode
      return inputs.map(s => mockEmbed(s));
    }

    const model = options?.model ?? process.env.OPENAI_EMBED_MODEL ?? 'text-embedding-3-small';

    const body = { model, input: inputs };

    const resp = await fetch(OPENAI_EMBED_ENDPOINT, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${this.apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: options?.signal
    });

    if (!resp.ok) {
      const t = await resp.text();
      throw new Error(`OpenAI embed error ${resp.status}: ${t}`);
    }

    const json = await resp.json();
    // shape: data: [{embedding: []}, ...]
    const out = (json.data ?? []).map((d: any) => d.embedding as number[]);
    if (out.length > 0 && !this.dimension) this.dimension = out[0].length;
    return out;
  }
}

function mockEmbed(s: string): number[] {
  // deterministic pseudo-embedding: hash into vector of length 8
  const dim = 8;
  const vec = new Array<number>(dim).fill(0);
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619) >>> 0;
  for (let i = 0; i < dim; i++) {
    h = (h * 1664525 + 1013904223) >>> 0;
    vec[i] = ((h % 1000) / 1000) * 2 - 1;
  }
  return vec;
}
