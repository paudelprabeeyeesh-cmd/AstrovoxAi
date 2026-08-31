import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Mock the Supabase client before api.js is imported (no realtime in Node 20).
vi.mock('../supabase', () => ({
  supabase: { auth: { getSession: async () => ({ data: { session: null } }) } },
}))

import { validateApiPath, apiRequest } from './api'

// ---------------------------------------------------------------------------
// Path validation (security)
// ---------------------------------------------------------------------------

describe('validateApiPath', () => {
  it('accepts normal backend paths', () => {
    expect(validateApiPath('/health')).toBe('/health')
    expect(validateApiPath('/api/status')).toBe('/api/status')
    expect(validateApiPath('/api/memory?limit=5')).toBe('/api/memory?limit=5')
  })

  it('rejects non-path input', () => {
    expect(validateApiPath('')).toBeNull()
    expect(validateApiPath(null)).toBeNull()
    expect(validateApiPath('health')).toBeNull()
  })

  it('rejects absolute URLs / scheme injection', () => {
    expect(validateApiPath('//evil.example.com/health')).toBeNull()
    expect(validateApiPath('/health?next=javascript:alert(1)')).toBeNull()
  })

  it('rejects control characters', () => {
    expect(validateApiPath('/health\u0000')).toBeNull()
    expect(validateApiPath('/hea\u001flth')).toBeNull()
  })

  it('rejects overly long paths', () => {
    expect(validateApiPath('/' + 'a'.repeat(300))).toBeNull()
  })

  it('blocks sensitive route groups', () => {
    expect(validateApiPath('/auth/login')).toBeNull()
    expect(validateApiPath('/storage/bucket/file')).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// apiRequest — transport behavior
// ---------------------------------------------------------------------------

describe('apiRequest', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function stubFetch(impl) {
    global.fetch = vi.fn(impl)
  }

  it('performs a GET with JSON headers and parses the body', async () => {
    stubFetch(async () => ({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ status: 'healthy' }),
    }))
    const res = await apiRequest({ path: '/health' })
    expect(global.fetch).toHaveBeenCalledOnce()
    expect(res).toEqual({ ok: true, status: 200, kind: 'response', data: { status: 'healthy' } })
  })

  it('sends a JSON body on POST and does not throw on non-JSON bodies', async () => {
    stubFetch(async () => ({ ok: true, status: 200, text: async () => '<html>gateway</html>' }))
    const res = await apiRequest({ method: 'POST', path: '/api/terminal/purge', body: { content: 'x' } })
    const [, init] = global.fetch.mock.calls[0]
    expect(init.method).toBe('POST')
    expect(init.body).toBe(JSON.stringify({ content: 'x' }))
    expect(res.ok).toBe(true)
    expect(res.data.raw).toBe('<html>gateway</html>')
  })

  it('returns kind=network when fetch rejects', async () => {
    stubFetch(async () => { throw new TypeError('fetch failed') })
    const res = await apiRequest({ path: '/health' })
    expect(res.ok).toBe(false)
    expect(res.kind).toBe('network')
    expect(res.status).toBe(0)
  })

  it('returns kind=timeout when the request exceeds the deadline', async () => {
    stubFetch((_url, init) => new Promise((_resolve, reject) => {
      init.signal.addEventListener('abort', () => {
        const err = new Error('aborted')
        err.name = 'AbortError'
        reject(err)
      })
    }))
    const res = await apiRequest({ path: '/health', timeoutMs: 50 })
    expect(res.ok).toBe(false)
    expect(res.kind).toBe('timeout')
    expect(res.detail).toMatch(/timed out/)
  })

  it('rejects invalid paths without touching the network', async () => {
    stubFetch(async () => { throw new Error('should not be called') })
    const res = await apiRequest({ path: '//evil.example.com' })
    expect(res.ok).toBe(false)
    expect(res.kind).toBe('invalid-path')
    expect(global.fetch).not.toHaveBeenCalled()
  })

  it('propagates non-2xx responses as ok=false with parsed detail', async () => {
    stubFetch(async () => ({
      ok: false,
      status: 401,
      text: async () => JSON.stringify({ detail: 'Authorization header required' }),
    }))
    const res = await apiRequest({ path: '/api/stats' })
    expect(res.ok).toBe(false)
    expect(res.status).toBe(401)
    expect(res.data.detail).toMatch(/Authorization/)
  })
})
