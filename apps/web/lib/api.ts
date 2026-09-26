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
  getHelpArticle: (slug: string) =>
    request<{ article: HelpArticle }>(`/support/articles/${encodeURIComponent(slug)}`),
  searchHelpArticles: (query: string) =>
    request<{ articles: HelpArticle[] }>(`/support/articles/search?q=${encodeURIComponent(query)}`),
  markArticleHelpful: (id: string, helpful: boolean) =>
    request<void>(`/support/articles/${id}/feedback`, {
      method: 'POST',
      body: JSON.stringify({ helpful }),
    }),

  // Tutorials
  getTutorials: (difficulty?: string) =>
    request<{ tutorials: Tutorial[] }>(`/cx/tutorials${difficulty ? `?difficulty=${difficulty}` : ''}`),
  startTutorial: (tutorialId: string) =>
    request<{ progress: TutorialProgress }>(`/cx/tutorials/${tutorialId}/start`, { method: 'POST' }),
  updateTutorialProgress: (tutorialId: string, currentStep: number) =>
    request<{ progress: TutorialProgress }>(`/cx/tutorials/${tutorialId}/progress`, {
      method: 'POST',
      body: JSON.stringify({ currentStep }),
    }),
  getTutorialProgress: () =>
    request<{ progress: TutorialProgress[] }>('/cx/tutorials/progress'),

  // Feedback
  submitFeedback: (type: string, rating?: number, comment?: string, pageUrl?: string) =>
    request<{ feedback: Feedback }>('/cx/feedback', {
      method: 'POST',
      body: JSON.stringify({ type, rating, comment, page_url: pageUrl }),
    }),
  getFeedback: (type?: string) =>
    request<{ feedback: Feedback[] }>(`/cx/feedback${type ? `?feedback_type=${type}` : ''}`),

  // NPS
  submitNps: (score: number, comment?: string, surveyType?: string) =>
    request<{ survey: NpsSurvey }>('/cx/nps', {
      method: 'POST',
      body: JSON.stringify({ score, comment, survey_type: surveyType }),
    }),
  getNpsStats: () =>
    request<{ stats: NpsStats }>('/cx/nps/stats'),

  // Feature Requests
  createFeatureRequest: (title: string, description: string) =>
    request<{ request: FeatureRequest }>('/cx/features', {
      method: 'POST',
      body: JSON.stringify({ title, description }),
    }),
  getFeatureRequests: (status?: string) =>
    request<{ requests: FeatureRequest[] }>(`/cx/features${status ? `?status=${status}` : ''}`),
  voteFeatureRequest: (requestId: string) =>
    request<{ request: FeatureRequest }>(`/cx/features/${requestId}/vote`, { method: 'POST' }),

  // Bug Reports
  createBugReport: (title: string, description: string, severity?: string, stepsToReproduce?: string) =>
    request<{ bug: BugReport }>('/cx/bugs', {
      method: 'POST',
      body: JSON.stringify({ title, description, severity, steps_to_reproduce: stepsToReproduce }),
    }),
  getBugReports: (status?: string) =>
    request<{ bugs: BugReport[] }>(`/cx/bugs${status ? `?status=${status}` : ''}`),
  updateBugStatus: (bugId: string, status: string) =>
    request<{ bug: BugReport }>(`/cx/bugs/${bugId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),

  // Customer Health
  getCustomerHealth: (userId?: string) =>
    request<{ health: CustomerHealth }>(`/cx/health${userId ? `/${userId}` : ''}`),

  // Support Analytics
  recordSupportAnalytic: (metricName: string, metricValue: number, period: string) =>
    request<{ analytic: SupportAnalytic }>('/cx/analytics', {
      method: 'POST',
      body: JSON.stringify({ metric_name: metricName, metric_value: metricValue, period }),
    }),
  getSupportAnalytics: (metricName?: string, period?: string) =>
    request<{ analytics: SupportAnalytic[] }>(`/cx/analytics${metricName ? `?metric_name=${metricName}` : ''}${period ? `&period=${period}` : ''}`),

  // Status Page
  getStatusSummary: () =>
    request<{ summary: StatusSummary }>('/cx/status'),
  getIncidents: (status?: string) =>
    request<{ incidents: StatusIncident[] }>(`/cx/incidents${status ? `?status=${status}` : ''}`),

  // Onboarding
  startOnboarding: () =>
    request<{ progress: OnboardingProgress }>('/cx/onboarding/start', { method: 'POST' }),
  completeOnboardingStep: (step: string) =>
    request<{ progress: OnboardingProgress }>('/cx/onboarding/step', {
      method: 'POST',
      body: JSON.stringify({ step }),
    }),
  completeOnboarding: () =>
    request<{ progress: OnboardingProgress }>('/cx/onboarding/complete', { method: 'POST' }),
  getOnboardingProgress: () =>
    request<{ progress: OnboardingProgress | null }>('/cx/onboarding'),

  // Live Chat
  createChatSession: (agentId?: string) =>
    request<{ session: LiveChatSession }>('/cx/chat/sessions', {
      method: 'POST',
      body: JSON.stringify({ agent_id: agentId }),
    }),
  sendChatMessage: (sessionId: string, message: string) =>
    request<{ message: ChatMessage }>(`/cx/chat/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),
  getChatMessages: (sessionId: string) =>
    request<{ messages: ChatMessage[] }>(`/cx/chat/sessions/${sessionId}/messages`),
  endChatSession: (sessionId: string) =>
    request<{ session: LiveChatSession }>(`/cx/chat/sessions/${sessionId}/end`, { method: 'POST' }),
  getChatSessions: () =>
    request<{ sessions: LiveChatSession[] }>('/cx/chat/sessions'),

  // Customer Portal
  getCustomerPortal: () =>
    request<{ portal: CustomerPortal }>('/cx/portal'),

  // Analytics
  getAnalyticsDashboard: (days?: number) =>
    request<{ data: AnalyticsDashboard }>(`/analytics/dashboard?days=${days ?? 7}`),
  getAnalyticsOverview: (days?: number) =>
    request<{ data: AnalyticsOverview }>(`/analytics/overview?days=${days ?? 7}`),
  getUsageStats: (days?: number) =>
    request<{ data: UsageStats }>(`/analytics/usage?days=${days ?? 7}`),
  getTokenAnalytics: (days?: number) =>
    request<{ data: TokenAnalytics }>(`/analytics/tokens?days=${days ?? 7}`),
  getCostAnalytics: (days?: number) =>
    request<{ data: CostAnalytics }>(`/analytics/costs?days=${days ?? 7}`),
  getModelPerformance: (days?: number) =>
    request<{ data: ModelPerformance }>(`/analytics/models?days=${days ?? 7}`),
  getGpuAnalytics: (days?: number) =>
    request<{ data: GpuAnalytics }>(`/analytics/gpu?days=${days ?? 7}`),
  getMemoryAnalytics: (days?: number) =>
    request<{ data: MemoryAnalytics }>(`/analytics/memory?days=${days ?? 7}`),
  getApiMetrics: (days?: number) =>
    request<{ data: ApiMetrics }>(`/analytics/api-metrics?days=${days ?? 7}`),
  getErrorAnalytics: (days?: number) =>
    request<{ data: ErrorAnalytics }>(`/analytics/errors?days=${days ?? 7}`),
  getRealtimeAnalytics: (days?: number) =>
    request<{ data: RealtimeAnalytics }>(`/analytics/realtime?days=${days ?? 1}`),

  // Monitoring
  getMonitoringDashboard: () =>
    request<MonitoringDashboard>('/monitoring/dashboard'),
  getMonitoringHealth: () =>
    request<HealthCheck>('/monitoring/health/detailed'),
  getMonitoringErrors: (limit?: number) =>
    request<{ errors: MonitoringError[]; summary: Record<string, unknown> }>(`/monitoring/errors?limit=${limit ?? 50}`),
  getMonitoringPerformance: () =>
    request<{ system: Record<string, unknown>; requests: Record<string, unknown> }>('/monitoring/performance'),
  getMonitoringUptime: () =>
    request<UptimeInfo>('/monitoring/uptime'),
  getMonitoringGpu: () =>
    request<{ gpu: Record<string, unknown>; available: boolean }>('/monitoring/gpu'),
  getMonitoringMemory: () =>
    request<{ memory: Record<string, unknown> }>('/monitoring/memory'),
  getMonitoringLatency: (hours?: number) =>
    request<{ data: LatencyMetrics }>(`/monitoring/latency?hours=${hours ?? 24}`),
  getMonitoringApiMetrics: () =>
    request<{ requests: Record<string, unknown>; latency: Record<string, unknown> }>('/monitoring/api-metrics'),
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

export interface AnalyticsDashboard {
  total_messages: number
  total_cost_usd: number
  realtime: RealtimeAnalytics
  usage: UsageStats
  tokens: TokenAnalytics
  costs: CostAnalytics
  performance: PerformanceAnalytics
  errors: ErrorAnalytics
  conversations: ConversationAnalytics
  models: ModelPerformance
  feature_adoption: FeatureAdoptionAnalytics
  user_behavior: UserBehaviorAnalytics
  revenue: RevenueAnalytics
}

export interface AnalyticsOverview {
  period_days: number
  usage: {
    total_requests: number
    total_tokens: number
    active_users: number
    avg_latency: number
    error_rate: number
  }
  ai_usage: {
    total_requests: number
    success_rate: number
    avg_latency: number
  }
  tokens: {
    total_tokens: number
    total_cost: number
  }
  costs: {
    total_cost: number
    trend: string
  }
  models: {
    model_count: number
    best_by_latency: string | null
    best_by_success: string | null
  }
  users: {
    active_users: number
    total_actions: number
  }
}

export interface UsageStats {
  total_requests: number
  total_tokens: number
  total_errors: number
  error_rate: number
  average_latency: number
  active_users: number
  total_users: number
}

export interface TokenAnalytics {
  period_days: number
  total_tokens: number
  total_input_tokens: number
  total_output_tokens: number
  total_cost: number
  avg_tokens_per_request: number
  tokens_by_user: Record<string, number>
  tokens_by_model: Record<string, number>
  tokens_by_provider: Record<string, number>
  tokens_by_hour: Record<number, number>
  tokens_by_day: Record<string, number>
  peak_hour: [number, number]
  peak_day: [string, number]
}

export interface CostAnalytics {
  period_days: number
  total_api_cost: number
  total_revenue: number
  net_margin: number
  cost_by_user: Record<string, number>
  cost_by_model: Record<string, number>
  cost_by_provider: Record<string, number>
  daily_costs: Record<string, number>
  trend: string
  mrr: number
  arr: number
  forecast_next_period: number
}

export interface PerformanceAnalytics {
  period_days: number
  total_requests: number
  avg_latency: number
  p50_latency: number
  p95_latency: number
  p99_latency: number
  max_latency: number
  min_latency: number
  avg_duration_ms: number
  throughput_rpm: number
}

export interface ErrorAnalytics {
  period_days: number
  total_events: number
  total_errors: number
  total_failed_requests: number
  total_requests: number
  error_rate: number
  error_rate_percent: number
  error_types: Record<string, number>
  errors_by_model: Record<string, number>
  errors_by_user: Record<string, number>
  error_timeline: Record<string, number>
}

export interface RealtimeAnalytics {
  generated_at: string
  period_days: number
  active_users: number
  active_sessions: number
  total_events: number
  events_per_minute: number
  requests_per_minute: number
  behavior_events: number
  revenue_today: number
  events_today: number
  cost_today: number
  top_pages: Array<[string, number]>
  top_features: Array<[string, number]>
}

export interface ConversationAnalytics {
  period_days: number
  total_conversations: number
  total_messages: number
  total_tokens: number
  total_cost: number
  avg_messages_per_conversation: number
  avg_tokens_per_conversation: number
  avg_duration_seconds: number
  sentiment_distribution: Record<string, number>
  model_distribution: Record<string, number>
  satisfaction_avg: number
}

export interface ModelPerformance {
  period_days: number
  models: Record<string, {
    requests: number
    success_rate: number
    error_rate: number
    avg_latency: number
    p50_latency: number
    p95_latency: number
    p99_latency: number
    avg_tokens: number
    total_cost: number
  }>
  best_by_latency: string | null
  best_by_success: string | null
  best_by_cost: string | null
}

export interface FeatureAdoptionAnalytics {
  period_days: number
  features: Record<string, {
    total_users: number
    adopted_users: number
    adoption_rate: number
    total_uses: number
    avg_uses_per_user: number
    category: string
  }>
  overall_adoption_rate: number
}

export interface UserBehaviorAnalytics {
  period_days: number
  total_behavior_events: number
  unique_users: number
  event_type_breakdown: Record<string, number>
  top_pages: Array<{ page: string; views: number }>
  avg_time_on_page: Record<string, number>
  avg_scroll_depth: Record<string, number>
  click_heatmap: Record<string, number>
}

export interface RevenueAnalytics {
  period_days: number
  total_revenue: number
  net_revenue: number
  refunds: number
  revenue_by_type: Record<string, { count: number; total: number }>
  revenue_by_plan: Record<string, { count: number; total: number }>
  daily_revenue: Record<string, number>
  top_customers: Record<string, number>
  mrr: number
  arr: number
  arpu: number
}

export interface GpuAnalytics {
  period_days: number
  gpu_available: boolean
  device_count: number
  device_ids: number[]
  avg_utilization_percent: number
  max_utilization_percent: number
  min_utilization_percent: number
  avg_memory_used_mb: number
  avg_memory_total_mb: number
  avg_temperature_c: number
  max_temperature_c: number
  min_temperature_c: number
  timeline: Array<{
    date: string
    avg_utilization_percent: number
    avg_memory_used_mb: number
    avg_temperature_c: number
  }>
}

export interface MemoryAnalytics {
  period_days: number
  total_mb: number
  avg_used_mb: number
  max_used_mb: number
  min_used_mb: number
  avg_available_mb: number
  avg_percent: number
  max_percent: number
  min_percent: number
  avg_swap_used_mb: number
  max_swap_used_mb: number
  timeline: Array<{
    date: string
    used_mb: number
    available_mb: number
    percent: number
    swap_used_mb: number
  }>
}

export interface ApiMetrics {
  period_days: number
  total_requests: number
  total_errors: number
  error_rate: number
  avg_latency_ms: number
  by_endpoint: Record<string, {
    count: number
    errors: number
    error_rate: number
    avg_latency_ms: number
    p95_latency_ms: number
    p99_latency_ms: number
    total_tokens: number
  }>
  by_method: Record<string, number>
  by_status: Record<string, number>
  by_model: Record<string, {
    count: number
    avg_latency_ms: number
    total_tokens: number
  }>
}

export interface MonitoringDashboard {
  status: string
  uptime: {
    uptime_seconds: number
    start_time: number
    status: string
  }
  system: Record<string, unknown>
  errors: Record<string, unknown>
  requests: Record<string, unknown>
  latency: Record<string, unknown>
}

export interface HealthCheck {
  status: string
  timestamp: number
  uptime: {
    uptime_seconds: number
    start_time: number
    status: string
  }
  system: {
    cpu: number
    memory: number
    disk: number
    gpu: {
      available: boolean
      devices: Array<Record<string, unknown>>
      utilization_percent: number
      memory_used_mb: number
      memory_total_mb: number
      temperature_c: number
    }
  }
  errors: {
    total: number
    by_severity: Record<string, number>
    by_type: Record<string, number>
  }
}

export interface MonitoringError {
  error_type: string
  message: string
  endpoint: string
  timestamp: number
  severity: string
}

export interface UptimeInfo {
  status: string
  uptime_seconds: number
  start_time: number
}

export interface LatencyMetrics {
  period_hours: number
  count: number
  avg_ms: number
  min_ms: number
  max_ms: number
  p50_ms: number
  p95_ms: number
  p99_ms: number
}
