
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api'

export interface FeedbackInput {
  requestId: string
  rating: number
  comment?: string
}

export async function submitFeedback(userId: string, feedback: FeedbackInput): Promise<void> {
  try {
    await fetch(`${API_BASE}/analytics/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, ...feedback }),
    })
  } catch {
    // swallow tracking errors
  }
}

export async function getFeedbackSummary(days = 30): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/analytics/feedback/summary?days=${days}`)
  if (!res.ok) throw new Error('Failed to fetch feedback summary')
  return res.json()
}

export async function getRecentFeedback(limit = 50): Promise<Array<Record<string, unknown>>> {
  const res = await fetch(`${API_BASE}/analytics/feedback/recent?limit=${limit}`)
  if (!res.ok) throw new Error('Failed to fetch recent feedback')
  return res.json()
}
