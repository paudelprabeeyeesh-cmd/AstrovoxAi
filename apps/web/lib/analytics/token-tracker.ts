
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api'

export interface TokenEvent {
  model: string
  promptTokens: number
  completionTokens: number
  cached?: boolean
}

export async function trackTokens(userId: string, event: TokenEvent): Promise<void> {
  try {
    await fetch(`${API_BASE}/analytics/tokens`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, ...event }),
    })
  } catch {
    // swallow tracking errors
  }
}

export async function getUserTokens(userId: string, days = 30): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/analytics/tokens?user_id=${encodeURIComponent(userId)}&days=${days}`)
  if (!res.ok) throw new Error('Failed to fetch tokens')
  return res.json()
}

export async function getTokenTrend(days = 7): Promise<Record<string, unknown>[]> {
  const res = await fetch(`${API_BASE}/analytics/tokens/trend?days=${days}`)
  if (!res.ok) throw new Error('Failed to fetch token trend')
  return res.json()
}
