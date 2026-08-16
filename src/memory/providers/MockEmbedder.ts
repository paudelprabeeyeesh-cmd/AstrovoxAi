import type { IEmbedder } from '../contracts/IEmbedder';

export class MockEmbedder implements IEmbedder {
  name = 'mock-embedder';
  private dim: number;
  constructor(dim = 8) { this.dim = dim; }
  getDimension(): number | undefined { return this.dim; }
  async embed(inputs: string[]): Promise<number[][]> {
    return inputs.map(s => mockEmbed(s, this.dim));
  }
}

function mockEmbed(s: string, dim: number): number[] {
  const vec = new Array<number>(dim).fill(0);
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619) >>> 0;
  for (let i = 0; i < dim; i++) {
    h = (h * 1664525 + 1013904223) >>> 0;
    vec[i] = ((h % 1000) / 1000) * 2 - 1;
  }
  return vec;
}
