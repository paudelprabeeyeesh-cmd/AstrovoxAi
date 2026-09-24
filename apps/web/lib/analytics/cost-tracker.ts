
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api'

export interface CostEvent {
  model: string
  promptTokens: number
  completionTokens: number
  cost: number
}

export async function trackCost(userId: string, event: CostEvent): Promise<void> {
  try {
    await fetch(`${API_BASE}/analytics/cost`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, ...event }),
    })
  } catch {
    // swallow tracking errors
  }
}

export async function getUserCost(userId: string, days = 30): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/analytics/cost?user_id=${encodeURIComponent(userId)}&days=${days}`)
  if (!res.ok) throw new Error('Failed to fetch cost')
  return res.json()
}
