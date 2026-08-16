export type SimilarityMetric = 'cosine' | 'dot' | 'euclidean';

export interface VectorRecord {
  id: string;
  vector: number[];
  metadata?: Record<string, any>;
  namespace?: string;
  createdAt?: string;
  deleted?: boolean; // soft-delete flag
}

export interface RetrievalResult {
  id: string;
  score: number;
  metadata?: Record<string, any>;
  vector?: number[];
}

export interface IVectorStore {
  name: string;
  init(): Promise<void>;
  upsert(records: VectorRecord[], options?: { batchSize?: number }): Promise<void>;
  query(embedding: number[], k?: number, options?: { namespace?: string; metric?: SimilarityMetric; filter?: Record<string, any> }): Promise<RetrievalResult[]>;
  fetch(ids: string[]): Promise<VectorRecord[]>;
  delete(ids: string[], options?: { soft?: boolean }): Promise<void>;
  close(): Promise<void>;
}
