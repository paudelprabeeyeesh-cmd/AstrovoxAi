
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api'

export interface SyntheticCheck {
  name: string
  url: string
  method?: string
  expectedStatus?: number
}

export async function runSyntheticCheck(check: SyntheticCheck): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/analytics/synthetic/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(check),
  })
  if (!res.ok) throw new Error('Failed to run synthetic check')
  return res.json()
}

export async function getSyntheticResults(limit = 50): Promise<Array<Record<string, unknown>>> {
  const res = await fetch(`${API_BASE}/analytics/synthetic/results?limit=${limit}`)
  if (!res.ok) throw new Error('Failed to fetch synthetic results')
  return res.json()
}
