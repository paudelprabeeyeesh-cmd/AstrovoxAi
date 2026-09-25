const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api'

async function getAuthToken(): Promise<string | null> {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('auth_token')
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  retries = 2,
  backoffMs = 300,
): Promise<T> {
  const token = await getAuthToken()
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }

  let lastError: Error | null = null

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
      })

      if (response.ok) {
        if (response.status === 204) return {} as T
        return response.json()
      }

      if (!response.ok && response.status < 500 && attempt === retries) {
        const error = await response.json().catch(() => ({ message: 'Request failed' }))
        throw new Error(error.message ?? `HTTP ${response.status}`)
      }

      if (!response.ok && response.status >= 500 && attempt < retries) {
        const delay = backoffMs * Math.pow(2, attempt)
        await new Promise((resolve) => setTimeout(resolve, delay))
        continue
      }

      const error = await response.json().catch(() => ({ message: 'Request failed' }))
      throw new Error(error.message ?? `HTTP ${response.status}`)
    } catch (error) {
      lastError = error as Error
      if (attempt < retries && lastError.message.includes('Failed to fetch')) {
        const delay = backoffMs * Math.pow(2, attempt)
        await new Promise((resolve) => setTimeout(resolve, delay))
        continue
      }
      throw lastError
    }
  }

  throw lastError ?? new Error('Request failed')
}

export const api = {
  get: <T>(endpoint: string) => request<T>(endpoint),
  post: <T>(endpoint: string, data: unknown) =>
    request<T>(endpoint, { method: 'POST', body: JSON.stringify(data) }),
  patch: <T>(endpoint: string, data: unknown) =>
    request<T>(endpoint, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (endpoint: string) => request<void>(endpoint, { method: 'DELETE' }),
  logError: (error: Error, context?: Record<string, unknown>) =>
    request<void>('/errors', {
      method: 'POST',
      body: JSON.stringify({
        message: error.message,
        stack: error.stack,
        name: error.name,
        ...context,
      }),
    }),

  searchSemantic: (query: string) =>
    request<SearchResult[]>('/search/semantic', {
      method: 'POST',
      body: JSON.stringify({ query }),
    }),

  searchKeyword: (query: string) =>
    request<SearchResult[]>('/search/keyword', {
      method: 'POST',
      body: JSON.stringify({ query }),
    }),

  searchHybrid: (query: string) =>
    request<SearchResult[]>('/search/hybrid', {
      method: 'POST',
      body: JSON.stringify({ query }),
    }),

  uploadDocument: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request<DocumentUploadResult>('/documents/upload', {
      method: 'POST',
      body: formData,
      headers: {},
    })
  },

  ingestWebsite: (url: string) =>
    request<IngestionJob>('/documents/ingest-website', {
      method: 'POST',
      body: JSON.stringify({ url }),
    }),

  ingestGitHub: (repo: string) =>
    request<IngestionJob>('/documents/ingest-github', {
      method: 'POST',
      body: JSON.stringify({ repo }),
    }),

  classifyMemory: (content: string) =>
    request<MemoryClassification>('/memory/classify', {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),

  getKnowledgeGraph: () =>
    request<KnowledgeGraph>('/knowledge/graph'),

  executeTool: (name: string, args: Record<string, unknown>) =>
    request<ToolExecutionResult>('/tools/execute', {
      method: 'POST',
      body: JSON.stringify({ name, args }),
    }),
}

export interface SearchResult {
  id: string
  title: string
  content: string
  score: number
  type: string
  createdAt: string
  metadata?: Record<string, unknown>
}

export interface DocumentUploadResult {
  id: string
  filename: string
  status: string
  chunks: number
  createdAt: string
}

export interface DocumentItem {
  id: string
  filename: string
  status: string
  chunks: number
  createdAt: string
}

export interface IngestionJob {
  id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  source: string
  progress: number
  error?: string
  createdAt: string
  completedAt?: string
}

export interface MemoryClassification {
  category: string
  confidence: number
  tags: string[]
  summary: string
}

export interface KnowledgeGraph {
  entities: KnowledgeEntity[]
  relationships: KnowledgeRelationship[]
}

export interface KnowledgeEntity {
  id: string
  name: string
  type: string
  properties: Record<string, unknown>
}

export interface KnowledgeRelationship {
  id: string
  sourceId: string
  targetId: string
  type: string
  properties: Record<string, unknown>
}

export interface ToolExecutionResult {
  toolName: string
  success: boolean
  result: unknown
  executionTime: number
  error?: string
}
