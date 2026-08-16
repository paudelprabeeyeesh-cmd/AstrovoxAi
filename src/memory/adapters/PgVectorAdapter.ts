import type { IVectorStore, VectorRecord, RetrievalResult, SimilarityMetric } from '../contracts/IVectorStore';
import { Client } from 'pg';

/**
 * PgVectorAdapter: attempts to connect to Postgres using DATABASE_URL. If connection fails
 * it falls back to an in-memory vector store implementation so the system remains functional
 * in mock/dev mode.
 */
export class PgVectorAdapter implements IVectorStore {
  name = 'pgvector-adapter';
  private client?: Client;
  private inMemory?: InMemoryVectorStore;
  private table = process.env.PGVECTOR_TABLE ?? 'memory_vectors';

  constructor(private databaseUrl?: string) {
    this.databaseUrl = databaseUrl ?? process.env.DATABASE_URL;
  }

  async init(): Promise<void> {
    if (!this.databaseUrl) {
      this.inMemory = new InMemoryVectorStore();
      return;
    }
    try {
      this.client = new Client({ connectionString: this.databaseUrl });
      await this.client.connect();
      // Ensure table exists (id, vector, metadata jsonb, namespace, created_at, deleted)
      const create = `CREATE TABLE IF NOT EXISTS ${this.table} (
        id TEXT PRIMARY KEY,
        vector VECTOR,
        metadata JSONB,
        namespace TEXT,
        created_at TIMESTAMPTZ DEFAULT now(),
        deleted BOOLEAN DEFAULT false
      )`;
      await this.client.query(create);
      // ivfflat index creation if pgvector supports it
      try {
        await this.client.query(`SELECT vector_dimensions FROM pgvector.vector_columns WHERE table_name = $1`, [this.table]);
      } catch (_) {
        // ignore
      }
    } catch (e) {
      console.error('PgVectorAdapter init failed, falling back to in-memory store:', e);
      this.inMemory = new InMemoryVectorStore();
    }
  }

  async upsert(records: VectorRecord[], options?: { batchSize?: number }): Promise<void> {
    if (this.inMemory) return this.inMemory.upsert(records, options);
    if (!this.client) throw new Error('Pg client not initialized');

    const batchSize = options?.batchSize ?? 128;
    for (let i = 0; i < records.length; i += batchSize) {
      const batch = records.slice(i, i + batchSize);
      const queries = batch.map(r => ({ text: `INSERT INTO ${this.table} (id, vector, metadata, namespace, created_at, deleted) VALUES ($1, $2::vector, $3, $4, $5, $6) ON CONFLICT (id) DO UPDATE SET vector = EXCLUDED.vector, metadata = EXCLUDED.metadata, namespace = EXCLUDED.namespace, created_at = EXCLUDED.created_at, deleted = EXCLUDED.deleted`, values: [r.id, `ARRAY[${r.vector.join(',')}]`, JSON.stringify(r.metadata ?? {}), r.namespace ?? null, r.createdAt ?? new Date().toISOString(), r.deleted ?? false] }));
      const client = this.client;
      const tx = await client.query('BEGIN');
      try {
        for (const q of queries) await client.query(q);
        await client.query('COMMIT');
      } catch (e) {
        await client.query('ROLLBACK');
        throw e;
      }
    }
  }

  async query(embedding: number[], k = 10, options?: { namespace?: string; metric?: SimilarityMetric; filter?: Record<string, any> }): Promise<RetrievalResult[]> {
    if (this.inMemory) return this.inMemory.query(embedding, k, options);
    if (!this.client) throw new Error('Pg client not initialized');

    // Simple query using cosine similarity via <-> operator if available
    const namespace = options?.namespace;
    const filterSQL = namespace ? `WHERE namespace = $2 AND deleted = false` : `WHERE deleted = false`;
    const sql = `SELECT id, metadata, vector FROM ${this.table} ${filterSQL} ORDER BY vector <#> $1 LIMIT $${namespace ? 3 : 2}`;
    // Note: $1 should be the embedding; pass as array literal
    const vals = namespace ? [embedding, namespace] : [embedding];
    const res = await this.client.query(sql, vals as any[]);
    const out: RetrievalResult[] = res.rows.map((r: any) => ({ id: r.id, metadata: r.metadata, score: 0, vector: r.vector }));
    return out.slice(0, k);
  }

  async fetch(ids: string[]): Promise<VectorRecord[]> {
    if (this.inMemory) return this.inMemory.fetch(ids);
    if (!this.client) throw new Error('Pg client not initialized');
    const res = await this.client.query(`SELECT id, vector, metadata, namespace, created_at, deleted FROM ${this.table} WHERE id = ANY($1)`, [ids]);
    return res.rows.map((r: any) => ({ id: r.id, vector: r.vector, metadata: r.metadata, namespace: r.namespace, createdAt: r.created_at }));
  }

  async delete(ids: string[], options?: { soft?: boolean }): Promise<void> {
    if (this.inMemory) return this.inMemory.delete(ids, options);
    if (!this.client) throw new Error('Pg client not initialized');
    if (options?.soft) {
      await this.client.query(`UPDATE ${this.table} SET deleted = true WHERE id = ANY($1)`, [ids]);
    } else {
      await this.client.query(`DELETE FROM ${this.table} WHERE id = ANY($1)`, [ids]);
    }
  }

  async close(): Promise<void> {
    if (this.client) await this.client.end();
    if (this.inMemory) this.inMemory.clear();
  }
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
