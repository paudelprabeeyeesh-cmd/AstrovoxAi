import type { IEmbedder } from '../contracts/IEmbedder';

export class OllamaEmbedder implements IEmbedder {
  name = 'ollama-embedder';
  private host?: string;
  private dimension?: number;

  constructor() {
    this.host = process.env.OLLAMA_HOST; // e.g., http://localhost:11434
  }

  async init(): Promise<void> { }

  getDimension(): number | undefined { return this.dimension; }

  async embed(inputs: string[], options?: { namespace?: string; model?: string; signal?: AbortSignal }): Promise<number[][]> {
    if (!this.host) return inputs.map(i => mockEmbed(i));

    // Ollama embedding API format may vary; attempt to call /embeddings
    const url = `${this.host.replace(/\/$/, '')}/embeddings`;
    const model = options?.model ?? process.env.OLLAMA_EMBED_MODEL ?? 'llama2';
    const body = { model, input: inputs };
    const resp = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal: options?.signal });
    if (!resp.ok) {
      const t = await resp.text();
      throw new Error(`Ollama embed error ${resp.status}: ${t}`);
    }
    const json = await resp.json();
    // try to parse common shapes
    if (Array.isArray(json) && json.length === inputs.length && json[0].embedding) return json.map((x: any) => x.embedding as number[]);
    if (json.data) return json.data.map((d: any) => d.embedding as number[]);
    // fallback
    return inputs.map(i => mockEmbed(i));
  }
}

function mockEmbed(s: string): number[] {
  const dim = 8;
  const vec = new Array<number>(dim).fill(0);
  let h = 0;
  for (let i = 0; i < s.length; i++) h = ((h << 5) - h) + s.charCodeAt(i);
  for (let i = 0; i < dim; i++) {
    h = (h * 1664525 + 1013904223) >>> 0;
    vec[i] = ((h % 1000) / 1000) * 2 - 1;
  }
  return vec;
}
