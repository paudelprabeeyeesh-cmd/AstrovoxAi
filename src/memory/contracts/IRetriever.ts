import { RetrievalResult } from './IVectorStore';

export interface IRetriever {
  /**
   * Retrieve relevant memory entries for a free text query or an embedding.
   * If embedding is provided, retrieval is embedding-based; otherwise text query will be embedded by an IEmbedder upstream.
   */
  retrieve(options: { query?: string; embedding?: number[]; sessionId?: string; namespace?: string; k?: number; recencyBoost?: number; filter?: Record<string, any>; signal?: AbortSignal }): Promise<RetrievalResult[]>;
}
