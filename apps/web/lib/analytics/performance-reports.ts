
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api'

export interface PerformanceReport {
  generatedAt: string
  windowDays: number
  orgAnalytics?: Record<string, unknown>
  userAnalytics?: Record<string, unknown>
  metrics?: string
  summary: Record<string, unknown>
}

export async function generatePerformanceReport(
  orgId?: string,
  userId?: string,
  days = 7,
): Promise<PerformanceReport> {
  const params = new URLSearchParams()
  if (orgId) params.set('org_id', orgId)
  if (userId) params.set('user_id', userId)
  params.set('days', String(days))
  const res = await fetch(`${API_BASE}/analytics/performance/report?${params.toString()}`)
  if (!res.ok) throw new Error('Failed to generate performance report')
  return res.json()
}

export async function exportPerformanceReportJson(report: PerformanceReport): Promise<string> {
  return JSON.stringify(report, null, 2)
}

export async function exportPerformanceReportCsv(report: PerformanceReport): Promise<string> {
  const summary = report.summary || {}
  const rows = Object.entries(summary).map(([metric, value]) => [metric, String(value)])
  return ['metric,value', ...rows.map((r) => r.join(','))].join('\n')
}
