
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api'

export interface FeatureUsageEvent {
  feature: string
  metadata?: Record<string, unknown>
}

export async function trackFeatureUse(userId: string, event: FeatureUsageEvent): Promise<void> {
  try {
    await fetch(`${API_BASE}/analytics/features`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, ...event }),
    })
  } catch {
    // swallow tracking errors
  }
}

export async function getFeatureUsage(days = 7): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/analytics/features?days=${days}`)
  if (!res.ok) throw new Error('Failed to fetch feature usage')
  return res.json()
}

export async function getFeatureAdoption(): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/analytics/features/adoption`)
  if (!res.ok) throw new Error('Failed to fetch feature adoption')
  return res.json()
}
