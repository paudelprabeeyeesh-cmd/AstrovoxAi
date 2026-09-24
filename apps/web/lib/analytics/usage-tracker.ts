
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api'

export interface UsageEvent {
  action: string
  metadata?: Record<string, unknown>
  timestamp?: string
}

export async function trackUsage(userId: string, event: UsageEvent): Promise<void> {
  try {
    await fetch(`${API_BASE}/analytics/usage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, ...event }),
    })
  } catch {
    // swallow tracking errors
  }
}

export async function getTopUsageActions(userId: string, days = 7, limit = 10): Promise<Record<string, unknown>[]> {
  const res = await fetch(`${API_BASE}/analytics/usage/top?user_id=${encodeURIComponent(userId)}&days=${days}&limit=${limit}`)
  if (!res.ok) throw new Error('Failed to fetch top usage actions')
  return res.json()
}

export async function getUserUsage(userId: string, days = 30): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/analytics/usage?user_id=${encodeURIComponent(userId)}&days=${days}`)
  if (!res.ok) throw new Error('Failed to fetch usage')
  return res.json()
}
