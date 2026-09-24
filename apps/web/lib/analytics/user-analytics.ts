
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api'

export interface UserAnalytics {
  userId: string
  windowDays: number
  generatedAt: string
  events: Array<Record<string, unknown>>
  usage: Record<string, unknown>
}

export async function getUserAnalytics(userId: string, days = 30): Promise<UserAnalytics> {
  const res = await fetch(`${API_BASE}/analytics/users/${encodeURIComponent(userId)}?days=${days}`)
  if (!res.ok) throw new Error('Failed to fetch user analytics')
  return res.json()
}

export async function getUserActivityTimeline(userId: string, days = 7): Promise<Array<Record<string, unknown>>> {
  const res = await fetch(`${API_BASE}/analytics/users/${encodeURIComponent(userId)}/timeline?days=${days}`)
  if (!res.ok) throw new Error('Failed to fetch activity timeline')
  return res.json()
}

export async function getUserRetention(userId: string): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/analytics/users/${encodeURIComponent(userId)}/retention`)
  if (!res.ok) throw new Error('Failed to fetch retention')
  return res.json()
}
