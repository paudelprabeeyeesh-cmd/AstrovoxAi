import type { IVectorStore, VectorRecord, RetrievalResult, SimilarityMetric } from '../contracts/IVectorStore';

/**
 * PineconeAdapter: When PINECONE_API_KEY and PINECONE_ENV are provided, this adapter will call Pinecone REST API.
 * If credentials are not provided it falls back to an in-memory store for local development and tests.
 */
export class PineconeAdapter implements IVectorStore {
  name = 'pinecone-adapter';
  private apiKey?: string;
  private env?: string;
  private indexName?: string;
  private inMemory?: InMemoryVectorStore;

  constructor() {
    this.apiKey = process.env.PINECONE_API_KEY;
    this.env = process.env.PINECONE_ENV;
    this.indexName = process.env.PINECONE_INDEX ?? 'astrovox';
  }

  async init(): Promise<void> {
    if (!this.apiKey || !this.env) { this.inMemory = new InMemoryVectorStore(); return; }
    // Optionally validate index exists; create if required using Pinecone REST API
  }

  async upsert(records: VectorRecord[], options?: { batchSize?: number }): Promise<void> {
    if (this.inMemory) return this.inMemory.upsert(records, options);
    // Implement Pinecone upsert via REST API if apiKey available
    const batchSize = options?.batchSize ?? 100;
    for (let i = 0; i < records.length; i += batchSize) {
      const batch = records.slice(i, i + batchSize);
      const body = { vectors: batch.map(r => ({ id: r.id, values: r.vector, metadata: r.metadata })) };
      const url = `https://${this.indexName}-${this.env}.svc.pinecone.io/vectors/upsert`;
      const resp = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Api-Key': this.apiKey! }, body: JSON.stringify(body) });
      if (!resp.ok) throw new Error(`Pinecone upsert error ${resp.status}`);
    }
  }

  async query(embedding: number[], k = 10, options?: { namespace?: string; metric?: SimilarityMetric; filter?: Record<string, any> }): Promise<RetrievalResult[]> {
    if (this.inMemory) return this.inMemory.query(embedding, k, options);
    const url = `https://${this.indexName}-${this.env}.svc.pinecone.io/query`;
    const body: any = { vector: embedding, topK: k };
    if (options?.namespace) body.namespace = options.namespace;
    if (options?.filter) body.filter = options.filter;
    const resp = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Api-Key': this.apiKey! }, body: JSON.stringify(body) });
    if (!resp.ok) throw new Error(`Pinecone query error ${resp.status}`);
    const json = await resp.json();
    const matches = json.matches ?? [];
    return matches.map((m: any) => ({ id: m.id, score: m.score, metadata: m.metadata }));
  }

  async fetch(ids: string[]): Promise<VectorRecord[]> {
    if (this.inMemory) return this.inMemory.fetch(ids);
    // Pinecone fetch endpoint
    const url = `https://${this.indexName}-${this.env}.svc.pinecone.io/vectors/fetch`;
    const resp = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Api-Key': this.apiKey! }, body: JSON.stringify({ ids }) });
    if (!resp.ok) throw new Error(`Pinecone fetch error ${resp.status}`);
    const json = await resp.json();
    const vectors = json.vectors ?? {};
    return Object.keys(vectors).map(id => ({ id, vector: vectors[id].values, metadata: vectors[id].metadata }));
  }

  async delete(ids: string[], options?: { soft?: boolean }): Promise<void> {
    if (this.inMemory) return this.inMemory.delete(ids, options);
    const url = `https://${this.indexName}-${this.env}.svc.pinecone.io/vectors/delete`;
    const resp = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Api-Key': this.apiKey! }, body: JSON.stringify({ ids }) });
    if (!resp.ok) throw new Error(`Pinecone delete error ${resp.status}`);
  }

  async close(): Promise<void> { if (this.inMemory) this.inMemory.clear(); }
}

class InMemoryVectorStore implements IVectorStore {
  name = 'inmemory-fallback';
  private store: Map<string, VectorRecord> = new Map();
  async init(): Promise<void> { }
  async upsert(records: VectorRecord[]) { for (const r of records) this.store.set(r.id, { ...r }); }
  async query(embedding: number[], k = 10) {
    const out: RetrievalResult[] = [];
    for (const v of this.store.values()) {
      if (v.deleted) continue;
      const score = cosineSimilarity(embedding, v.vector ?? []);
      out.push({ id: v.id, score, metadata: v.metadata, vector: v.vector });
    }
    out.sort((a, b) => b.score - a.score);
    return out.slice(0, k);
  }
  async fetch(ids: string[]) { return ids.map(id => this.store.get(id)).filter(Boolean) as VectorRecord[]; }
  async delete(ids: string[], options?: { soft?: boolean }) { for (const id of ids) { const v = this.store.get(id); if (!v) continue; if (options?.soft) { v.deleted = true; this.store.set(id, v); } else this.store.delete(id); } }
  async close() { this.store.clear(); }
  clear() { this.store.clear(); }
}

function dot(a: number[], b: number[]) { let s = 0; for (let i = 0; i < Math.min(a.length, b.length); i++) s += a[i] * b[i]; return s; }
function len(a: number[]) { let s = 0; for (let i = 0; i < a.length; i++) s += a[i] * a[i]; return Math.sqrt(s); }
function cosineSimilarity(a: number[], b: number[]) { const la = len(a); const lb = len(b); if (la === 0 || lb === 0) return 0; return dot(a, b) / (la * lb); }
