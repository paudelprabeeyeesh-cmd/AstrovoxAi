export const memoryConfig = {
  defaultVectorStore: process.env.MEMORY_VECTOR_STORE ?? 'pgvector', // 'pgvector' | 'pinecone' | 'inmemory'
  pg: {
    table: process.env.PGVECTOR_TABLE ?? 'memory_vectors',
    connectionString: process.env.DATABASE_URL
  },
  pinecone: {
    apiKey: process.env.PINECONE_API_KEY,
    env: process.env.PINECONE_ENV,
    index: process.env.PINECONE_INDEX ?? 'astrovox'
  },
  embedder: {
    default: process.env.MEMORY_EMBEDDER ?? 'mock', // 'openai' | 'gemini' | 'ollama' | 'mock'
    model: process.env.MEMORY_EMBED_MODEL
  },
  session: {
    maxItems: parseInt(process.env.MEMORY_SESSION_MAX_ITEMS || '200', 10),
    ttlSeconds: parseInt(process.env.MEMORY_SESSION_TTL || '3600', 10)
  }
};
