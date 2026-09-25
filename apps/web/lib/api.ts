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

  // Help Center
  getHelpArticles: (category?: string) =>
    request<{ articles: HelpArticle[] }>(`/support/articles${category ? `?category=${category}` : ''}`),
  getHelpArticle: (id: string) =>
    request<{ article: HelpArticle }>(`/support/articles/${id}`),
  searchHelpArticles: (query: string) =>
    request<{ articles: HelpArticle[] }>(`/support/articles/search?q=${encodeURIComponent(query)}`),

  // Tutorials
  getTutorials: (difficulty?: string) =>
    request<{ tutorials: Tutorial[] }>(`/support/tutorials${difficulty ? `?difficulty=${difficulty}` : ''}`),
  startTutorial: (tutorialId: string) =>
    request<{ progress: TutorialProgress }>(`/support/tutorials/${tutorialId}/start`, { method: 'POST' }),
  updateTutorialProgress: (tutorialId: string, currentStep: number) =>
    request<{ progress: TutorialProgress }>(`/support/tutorials/${tutorialId}/progress`, {
      method: 'POST',
      body: JSON.stringify({ currentStep }),
    }),
  getTutorialProgress: () =>
    request<{ progress: TutorialProgress[] }>('/support/tutorials/progress'),

  // Feedback
  submitFeedback: (type: string, rating?: number, comment?: string, pageUrl?: string) =>
    request<{ feedback: Feedback }>('/support/feedback', {
      method: 'POST',
      body: JSON.stringify({ type, rating, comment, page_url: pageUrl }),
    }),
  getFeedback: (type?: string) =>
    request<{ feedback: Feedback[] }>(`/support/feedback${type ? `?feedback_type=${type}` : ''}`),

  // NPS
  submitNps: (score: number, comment?: string, surveyType?: string) =>
    request<{ survey: NpsSurvey }>('/support/nps', {
      method: 'POST',
      body: JSON.stringify({ score, comment, survey_type: surveyType }),
    }),
  getNpsStats: () =>
    request<{ stats: NpsStats }>('/support/nps/stats'),

  // Feature Requests
  createFeatureRequest: (title: string, description: string) =>
    request<{ request: FeatureRequest }>('/support/features', {
      method: 'POST',
      body: JSON.stringify({ title, description }),
    }),
  getFeatureRequests: (status?: string) =>
    request<{ requests: FeatureRequest[] }>(`/support/features${status ? `?status=${status}` : ''}`),
  voteFeatureRequest: (requestId: string) =>
    request<{ request: FeatureRequest }>(`/support/features/${requestId}/vote`, { method: 'POST' }),

  // Bug Reports
  createBugReport: (title: string, description: string, severity?: string, stepsToReproduce?: string) =>
    request<{ bug: BugReport }>('/support/bugs', {
      method: 'POST',
      body: JSON.stringify({ title, description, severity, steps_to_reproduce: stepsToReproduce }),
    }),
  getBugReports: (status?: string) =>
    request<{ bugs: BugReport[] }>(`/support/bugs${status ? `?status=${status}` : ''}`),
  updateBugStatus: (bugId: string, status: string) =>
    request<{ bug: BugReport }>(`/support/bugs/${bugId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),

  // Customer Health
  getCustomerHealth: (userId?: string) =>
    request<{ health: CustomerHealth }>(`/support/health${userId ? `/${userId}` : ''}`),

  // Support Analytics
  recordSupportAnalytic: (metricName: string, metricValue: number, period: string) =>
    request<{ analytic: SupportAnalytic }>('/support/analytics', {
      method: 'POST',
      body: JSON.stringify({ metric_name: metricName, metric_value: metricValue, period }),
    }),
  getSupportAnalytics: (metricName?: string, period?: string) =>
    request<{ analytics: SupportAnalytic[] }>(`/support/analytics${metricName ? `?metric_name=${metricName}` : ''}${period ? `&period=${period}` : ''}`),

  // Status Page
  getStatusSummary: () =>
    request<{ summary: StatusSummary }>('/support/status'),
  getIncidents: (status?: string) =>
    request<{ incidents: StatusIncident[] }>(`/support/incidents${status ? `?status=${status}` : ''}`),

  // Onboarding
  startOnboarding: () =>
    request<{ progress: OnboardingProgress }>('/support/onboarding/start', { method: 'POST' }),
  completeOnboardingStep: (step: string) =>
    request<{ progress: OnboardingProgress }>('/support/onboarding/step', {
      method: 'POST',
      body: JSON.stringify({ step }),
    }),
  completeOnboarding: () =>
    request<{ progress: OnboardingProgress }>('/support/onboarding/complete', { method: 'POST' }),
  getOnboardingProgress: () =>
    request<{ progress: OnboardingProgress | null }>('/support/onboarding'),

  // Live Chat
  createChatSession: (agentId?: string) =>
    request<{ session: LiveChatSession }>('/support/chat/sessions', {
      method: 'POST',
      body: JSON.stringify({ agent_id: agentId }),
    }),
  sendChatMessage: (sessionId: string, message: string) =>
    request<{ message: ChatMessage }>(`/support/chat/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),
  getChatMessages: (sessionId: string) =>
    request<{ messages: ChatMessage[] }>(`/support/chat/sessions/${sessionId}/messages`),
  endChatSession: (sessionId: string) =>
    request<{ session: LiveChatSession }>(`/support/chat/sessions/${sessionId}/end`, { method: 'POST' }),
  getChatSessions: () =>
    request<{ sessions: LiveChatSession[] }>('/support/chat/sessions'),

  // Customer Portal
  getCustomerPortal: () =>
    request<{ portal: CustomerPortal }>('/support/portal'),
}

// ============================================================================
// Type Definitions
// ============================================================================

export interface HelpArticle {
  id: string
  slug: string
  title: string
  content: string
  category: string
  tags: string[]
  views: number
  helpful_count: number
  not_helpful_count: number
  created_at: number
  updated_at: number
}

export interface Tutorial {
  id: string
  title: string
  description: string
  steps: Array<Record<string, unknown>>
  difficulty: string
  estimated_time: number
  created_at: number
  updated_at: number
}

export interface TutorialProgress {
  id: string
  user_id: string
  tutorial_id: string
  current_step: number
  completed: boolean
  started_at: number
  completed_at?: number
}

export interface Feedback {
  id: string
  user_id: string
  type: string
  rating?: number
  comment?: string
  page_url?: string
  created_at: number
}

export interface NpsSurvey {
  id: string
  user_id: string
  score: number
  comment?: string
  survey_type: string
  created_at: number
}

export interface NpsStats {
  average: number
  total: number
  promoters: number
  passives: number
  detractors: number
}

export interface FeatureRequest {
  id: string
  user_id: string
  title: string
  description: string
  votes: number
  status: string
  created_at: number
}

export interface BugReport {
  id: string
  user_id: string
  title: string
  description: string
  severity: string
  status: string
  steps_to_reproduce?: string
  created_at: number
}

export interface CustomerHealth {
  id: string
  user_id: string
  score: number
  factors: Record<string, number>
  last_calculated: number
  created_at: number
}

export interface SupportAnalytic {
  id: string
  metric_name: string
  metric_value: number
  period: string
  created_at: number
}

export interface StatusIncident {
  id: string
  title: string
  description: string
  status: string
  affected_services: string[]
  started_at: number
  resolved_at?: number
  created_at: number
}

export interface StatusSummary {
  status: string
  active_incidents: number
  total_incidents: number
  services: string[]
}

export interface OnboardingProgress {
  id: string
  user_id: string
  current_step: number
  completed_steps: string[]
  completed: boolean
  started_at: number
  completed_at?: number
}

export interface LiveChatSession {
  id: string
  user_id: string
  agent_id?: string
  status: string
  started_at: number
  ended_at?: number
}

export interface ChatMessage {
  id: string
  session_id: string
  sender_id: string
  sender_type: string
  message: string
  created_at: number
}

export interface CustomerPortal {
  health: CustomerHealth
  tickets: Ticket[]
  onboarding: OnboardingProgress | null
}

export interface Ticket {
  id: string
  tenant_id: string
  user_id: string
  subject: string
  description: string
  priority: string
  status: string
  category: string
  assigned_to?: string
  tags: string[]
  created_at: number
  updated_at: number
  resolved_at?: number
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
