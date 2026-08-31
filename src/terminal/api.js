import { supabase } from '../supabase'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const DEFAULT_TIMEOUT_MS = 10000

/**
 * Get current Supabase auth token (reuses the existing auth system).
 */
export async function getAuthToken() {
  const { data: { session } } = await supabase.auth.getSession()
  return session?.access_token || null
}

/**
 * Validate a terminal-provided API path before it is ever placed in a URL.
 * Only same-origin backend paths are allowed; schemes, hosts, query strings
 * with script content and control characters are rejected.
 */
export function validateApiPath(rawPath) {
  if (typeof rawPath !== 'string') return null
  const path = rawPath.trim()
  if (!path || path.length > 200) return null
  if (!path.startsWith('/') || path.startsWith('//')) return null
  // eslint-disable-next-line no-control-regex
  if (/[\u0000-\u001f\u007f]/.test(path)) return null
  if (/[?&].*(<|>|javascript:|script)/i.test(path)) return null
  if (/^\/(auth|storage)\b/i.test(path)) return null // sensitive route groups
  if (!/^\/[A-Za-z0-9\-._~/?=&]*$/.test(path)) return null
  return path
}

/**
 * Perform an authenticated request against the backend with timeout support.
 * Never throws raw network errors upward; returns a structured result.
 */
export async function apiRequest({ method = 'GET', path, body = null, timeoutMs = DEFAULT_TIMEOUT_MS }) {
  const safePath = validateApiPath(path)
  if (!safePath) {
    return { ok: false, status: 0, kind: 'invalid-path', detail: 'Invalid endpoint path' }
  }

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const headers = { 'Content-Type': 'application/json' }
    const token = await getAuthToken()
    if (token) headers['Authorization'] = `Bearer ${token}`

    const response = await fetch(`${API_BASE_URL}${safePath}`, {
      method,
      headers,
      signal: controller.signal,
      body: body ? JSON.stringify(body) : undefined,
    })

    let data = null
    const text = await response.text()
    try { data = text ? JSON.parse(text) : null } catch { data = { raw: text.slice(0, 2000) } }

    return { ok: response.ok, status: response.status, kind: 'response', data }
  } catch (error) {
    if (error.name === 'AbortError') {
      return { ok: false, status: 0, kind: 'timeout', detail: `Request timed out after ${timeoutMs}ms` }
    }
    return { ok: false, status: 0, kind: 'network', detail: error.message || 'Network request failed' }
  } finally {
    clearTimeout(timer)
  }
}

export { API_BASE_URL }
