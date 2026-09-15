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
}