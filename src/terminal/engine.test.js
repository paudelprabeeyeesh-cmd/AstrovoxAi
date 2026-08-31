import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Mock the Supabase client before engine -> api -> supabase is imported.
vi.mock('../supabase', () => ({
  supabase: { auth: { getSession: async () => ({ data: { session: null } }) } },
}))

import {
  parseCommand,
  executeCommand,
  suggestCommands,
  completeInput,
  commandNames,
  MAX_INPUT_LENGTH,
} from './engine'
import * as api from './api'

// Integration-level tests here use the real engine but a mocked apiRequest,
// so command wiring (paths, methods, payload shaping) is verified without a
// live backend.

function mockApi(impl) {
  return vi.spyOn(api, 'apiRequest').mockImplementation(impl)
}

beforeEach(() => {
  vi.restoreAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

// ---------------------------------------------------------------------------
// Parser unit tests
// ---------------------------------------------------------------------------

describe('parseCommand', () => {
  it('parses a simple command', () => {
    expect(parseCommand('/help')).toEqual({ name: 'help', args: [], error: null })
  })

  it('trims whitespace and lowercases the command', () => {
    expect(parseCommand('  /HELP  ')).toEqual({ name: 'help', args: [], error: null })
  })

  it('splits arguments', () => {
    expect(parseCommand('/inject remember the cake')).toEqual({
      name: 'inject',
      args: ['remember', 'the', 'cake'],
      error: null,
    })
  })

  it('resolves aliases', () => {
    expect(parseCommand('/h').name).toBe('help')
    expect(parseCommand('/?').name).toBe('help')
    expect(parseCommand('/cls').name).toBe('clear')
    expect(parseCommand('/st').name).toBe('stats')
    expect(parseCommand('/mem').name).toBe('memory')
    expect(parseCommand('/hp').name).toBe('health')
    expect(parseCommand('/u').name).toBe('usage')
    expect(parseCommand('/s').name).toBe('status')
  })

  it('returns an error for empty input', () => {
    const res = parseCommand('   ')
    expect(res.error).toBeNull()
    expect(res.name).toBeNull()
  })

  it('rejects input without a leading slash', () => {
    expect(parseCommand('help').error).toMatch(/commands start with/)
  })

  it('rejects over-long commands', () => {
    const res = parseCommand('/echo ' + 'x'.repeat(MAX_INPUT_LENGTH + 1))
    expect(res.error).toMatch(/too long/)
  })

  it('rejects control characters (injection guard)', () => {
    expect(parseCommand('/echo a\u0000b').error).toMatch(/forbidden control characters/)
    expect(parseCommand('/echo a\u001bb').error).toMatch(/forbidden control characters/)
  })

  it('rejects shell metacharacters in the command name', () => {
    expect(parseCommand('/echo;rm -rf').error).toMatch(/Invalid command name/)
    expect(parseCommand('/../../etc').error).toMatch(/Invalid command name/)
  })

  it('strips shell metacharacters from arguments', () => {
    const res = parseCommand('/echo safe`rm -rf`$(x)$PATH')
    expect(res.args[0]).toBe('saferm')
    expect(res.args[1]).not.toMatch(/[`$()]/)
  })
})

// ---------------------------------------------------------------------------
// Autocomplete
// ---------------------------------------------------------------------------

describe('suggestions', () => {
  it('suggests commands by prefix', () => {
    const suggestions = suggestCommands('/st')
    expect(suggestions).toContain('status')
    expect(suggestions).toContain('stats')
  })

  it('returns nothing for non-slash input', () => {
    expect(suggestCommands('st')).toEqual([])
  })

  it('completes a unique prefix', () => {
    const { input, matches } = completeInput('/hea')
    expect(matches).toEqual(['health'])
    expect(input).toBe('/health ')
  })

  it('keeps input when ambiguous', () => {
    const { input, matches } = completeInput('/st')
    expect(matches.length).toBeGreaterThan(1)
    expect(input).toBe('/st')
  })
})

// ---------------------------------------------------------------------------
// Local commands
// ---------------------------------------------------------------------------

describe('local commands', () => {
  it('lists every registered command in /help', () => {
    return executeCommand('/help', {}).then((res) => {
      expect(res.ok).toBe(true)
      const text = res.lines.map((l) => l.text).join('\n')
      for (const name of commandNames()) {
        expect(text).toContain(`/${name}`)
      }
    })
  })

  it('clear calls ctx.clear', async () => {
    const clear = vi.fn()
    const res = await executeCommand('/clear', { clear })
    expect(clear).toHaveBeenCalled()
    expect(res.ok).toBe(true)
  })

  it('echo requires an argument', async () => {
    const res = await executeCommand('/echo', {})
    expect(res.ok).toBe(false)
    expect(res.lines[0].text).toMatch(/Invalid arguments/)
  })

  it('echo prints sanitized text', async () => {
    const res = await executeCommand('/echo hello world', {})
    expect(res.lines[0].text).toContain('hello world')
  })

  it('unknown commands suggest alternatives and fail', async () => {
    const res = await executeCommand('/heal', {})
    expect(res.ok).toBe(false)
    expect(res.failure).toBe(true)
    const text = res.lines.map((l) => l.text).join('\n')
    expect(text).toContain('Did you mean')
  })

  it('date and uptime execute locally without the backend', async () => {
    const spy = mockApi(async () => ({ ok: true, status: 200, data: {} }))
    await executeCommand('/date', {})
    await executeCommand('/uptime', {})
    expect(spy).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// Backend integration (mocked transport)
// ---------------------------------------------------------------------------

describe('backend commands', () => {
  it('/health GETs /health', async () => {
    const spy = mockApi(async () => ({ ok: true, status: 200, kind: 'response', data: { status: 'healthy', service: 'x', version: '1' } }))
    const res = await executeCommand('/health', {})
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({ path: '/health' }))
    expect(res.ok).toBe(true)
    expect(res.lines[0].text).toMatch(/healthy/)
  })

  it('/status GETs /api/status and renders fields', async () => {
    mockApi(async () => ({
      ok: true, status: 200, kind: 'response',
      data: { status: 'OK', service: 'astravox-ai-api', version: '2.0.0', timestamp: 'now' },
    }))
    const res = await executeCommand('/status', { userEmail: 'a@b.c', totalItems: 7 })
    expect(res.ok).toBe(true)
    const text = res.lines.map((l) => l.text).join('\n')
    expect(text).toContain('astravox-ai-api')
    expect(text).toContain('7 rows mapped')
  })

  it('/stats GETs /api/stats (auth)', async () => {
    const spy = mockApi(async () => ({
      ok: true, status: 200, kind: 'response',
      data: { stats: { total_conversations: 3, total_memory_entries: 5, user_tier: 'pro' } },
    }))
    const res = await executeCommand('/stats', {})
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({ path: '/api/stats' }))
    const text = res.lines.map((l) => l.text).join('\n')
    expect(text).toContain('pro')
  })

  it('/memory validates the count argument', async () => {
    const spy = mockApi(async () => ({ ok: true, status: 200, kind: 'response', data: { memory: [] } }))
    const bad = await executeCommand('/memory abc', {})
    expect(bad.ok).toBe(false)
    expect(spy).not.toHaveBeenCalled()

    const ok = await executeCommand('/memory 5', {})
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({ path: '/api/memory?limit=5' }))
    expect(ok.ok).toBe(true)
  })

  it('/inject POSTs to /api/terminal/inject with content', async () => {
    const spy = mockApi(async () => ({
      ok: true, status: 200, kind: 'response',
      data: { status: 'OK', memory: { id: 42, content: 'note to self' } },
    }))
    const res = await executeCommand('/inject note to self', {})
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({
      method: 'POST',
      path: '/api/terminal/inject',
      body: { content: 'note to self' },
    }))
    expect(res.ok).toBe(true)
    expect(res.lines.map((l) => l.text).join('\n')).toContain('42')
  })

  it('/inject requires content', async () => {
    const spy = mockApi(async () => ({ ok: true, status: 200, data: {} }))
    const res = await executeCommand('/inject', {})
    expect(res.ok).toBe(false)
    expect(spy).not.toHaveBeenCalled()
  })

  it('/purge POSTs to /api/terminal/purge', async () => {
    const spy = mockApi(async () => ({ ok: true, status: 200, kind: 'response', data: { deleted: 4 } }))
    const res = await executeCommand('/purge', {})
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({ method: 'POST', path: '/api/terminal/purge' }))
    expect(res.lines.map((l) => l.text).join('\n')).toContain('Deleted 4')
  })

  it('/usage GETs /api/terminal/usage', async () => {
    const spy = mockApi(async () => ({ ok: true, status: 200, kind: 'response', data: { used: 9, limit: 50, resets: 'daily (UTC)' } }))
    const res = await executeCommand('/usage', {})
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({ path: '/api/terminal/usage' }))
    expect(res.lines.map((l) => l.text).join('\n')).toContain('9 / 50')
  })

  it('/api command validates and forwards endpoints', async () => {
    const spy = mockApi(async () => ({ ok: true, status: 200, kind: 'response', data: { message: 'hi' } }))
    const bad = await executeCommand('/api', {})
    expect(bad.ok).toBe(false)

    const good = await executeCommand('/api /health', {})
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({ path: '/health' }))
    expect(good.ok).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// Error handling & network failures
// ---------------------------------------------------------------------------

describe('failure handling', () => {
  it('surfaces auth errors as 401 guidance', async () => {
    mockApi(async () => ({ ok: false, status: 401, kind: 'response', data: { detail: 'Authorization header required' } }))
    const res = await executeCommand('/stats', {})
    expect(res.failure).toBe(true)
    expect(res.lines.map((l) => l.text).join('\n')).toMatch(/Unauthorized/)
  })

  it('surfaces rate limits as warnings', async () => {
    mockApi(async () => ({ ok: false, status: 429, kind: 'response', data: { detail: 'Daily AI quota exceeded: 50' } }))
    const res = await executeCommand('/usage', {})
    expect(res.lines.map((l) => l.text).join('\n')).toMatch(/Rate limited/)
  })

  it('surfaces generic backend errors with the status code', async () => {
    mockApi(async () => ({ ok: false, status: 500, kind: 'response', data: { detail: 'boom' } }))
    const res = await executeCommand('/purge', {})
    expect(res.failure).toBe(true)
    expect(res.lines.map((l) => l.text).join('\n')).toMatch(/Backend error 500: boom/)
  })

  it('surfaces network failures', async () => {
    mockApi(async () => ({ ok: false, status: 0, kind: 'network', detail: 'fetch failed' }))
    const res = await executeCommand('/health', {})
    expect(res.failure).toBe(true)
    expect(res.lines.map((l) => l.text).join('\n')).toMatch(/Backend unreachable/)
  })

  it('surfaces timeouts', async () => {
    mockApi(async () => ({ ok: false, status: 0, kind: 'timeout', detail: 'Request timed out after 5000ms' }))
    const res = await executeCommand('/ping', {})
    expect(res.failure).toBe(true)
    expect(res.lines.map((l) => l.text).join('\n')).toMatch(/timed out/)
  })

  it('catches crashing commands instead of throwing', async () => {
    mockApi(async () => { throw new Error('socket exploded') })
    const res = await executeCommand('/status', {})
    expect(res.ok).toBe(false)
    expect(res.lines.map((l) => l.text).join('\n')).toMatch(/Command crashed/)
  })
})
