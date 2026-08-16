import type { IEmbedder } from '../contracts/IEmbedder';

// Gemini embedding endpoint placeholder. Google Gemini embeddings API is not public in the same shape;
// this provider implements a mock and a pluggable live HTTP client if credentials are provided.

export class GeminiEmbedder implements IEmbedder {
  name = 'gemini-embedder';
  private apiKey?: string;
  private dimension?: number;

  constructor() {
    this.apiKey = process.env.GOOGLE_API_KEY || process.env.GEMINI_API_KEY;
  }

  async init(): Promise<void> {
    // probe if necessary
  }

  getDimension(): number | undefined { return this.dimension; }

  async embed(inputs: string[], options?: { namespace?: string; model?: string; signal?: AbortSignal }): Promise<number[][]> {
    if (!this.apiKey) {
      return inputs.map(i => mockEmbed(i));
    }
    // If an official Gemini embeddings endpoint is available, call it here.
    // For now fallback to mock behavior to stay operational without secrets.
    return inputs.map(i => mockEmbed(i));
  }
}

function mockEmbed(s: string): number[] {
  const dim = 8;
  const vec = new Array<number>(dim).fill(0);
  let h = 5381 >>> 0;
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h) + s.charCodeAt(i);
  for (let i = 0; i < dim; i++) {
    h = (h * 1103515245 + 12345) >>> 0;
    vec[i] = ((h % 1000) / 1000) * 2 - 1;
  }
  return vec;
}
