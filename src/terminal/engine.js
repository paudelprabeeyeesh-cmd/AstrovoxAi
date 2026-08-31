import { apiRequest, API_BASE_URL } from './api'

/**
 * ASTRAVOX Terminal Command Engine.
 * Pure, testable logic: parse -> validate -> execute -> structured result.
 * A result is { lines: Array<{text, tone}>, tone, data?, failure? }.
 * Tones: 'out' (default), 'ok', 'warn', 'err', 'info', 'dim'.
 */

export const MAX_INPUT_LENGTH = 500

// Characters that have no business inside a terminal command.
// eslint-disable-next-line no-control-regex
const DANGEROUS_CHARS = /[\u0000-\u0008\u000b-\u001f\u007f]/

export const HELP_HEADER = [
  { text: '   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', tone: 'dim' },
  { text: '   📟  AVAILABLE COMMANDS:', tone: 'info' },
  { text: '   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', tone: 'dim' },
]

export const HELP_FOOTER = [
  { text: '   Shortcuts: ↑/↓ history · Tab autocomplete · Ctrl+L clear · Ctrl+Shift+C copy', tone: 'dim' },
  { text: '   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', tone: 'dim' },
]

export const ALIASES = {
  h: 'help',
  '?': 'help',
  s: 'status',
  stat: 'stats',
  st: 'stats',
  hp: 'health',
  mem: 'memory',
  u: 'usage',
  cls: 'clear',
  version: 'api',
  ver: 'api',
}

const COMMANDS = new Map()

export function registerCommand(spec) {
  COMMANDS.set(spec.name, spec)
}

export function getCommand(name) {
  return COMMANDS.get(name) || null
}

export function commandNames() {
  return [...COMMANDS.keys()].sort()
}

/**
 * Parse a raw input line into a command invocation.
 * Returns { name, args, error? } — `error` is a user-friendly message.
 */
export function parseCommand(rawInput) {
  const input = String(rawInput ?? '').trim()
  if (!input) return { name: null, args: [], error: null }
  if (input.length > MAX_INPUT_LENGTH) {
    return { name: null, args: [], error: `Command too long (max ${MAX_INPUT_LENGTH} characters)` }
  }
  if (DANGEROUS_CHARS.test(input)) {
    return { name: null, args: [], error: 'Command contains forbidden control characters' }
  }
  if (!input.startsWith('/')) {
    return { name: null, args: [], error: 'Unknown input: commands start with "/". Type /help.' }
  }

  const parts = input.slice(1).split(/\s+/).filter(Boolean)
  const rawName = (parts[0] || '').toLowerCase()
  // Commands are plain identifiers only — blocks shell metacharacter tricks.
  if (!/^[a-z?][a-z0-9?-]*$/.test(rawName)) {
    return { name: null, args: [], error: `Invalid command name: "/${rawName}"` }
  }
  const name = ALIASES[rawName] || rawName
  const args = parts.slice(1).map((a) => a.replace(/["'`;|$&<>\\{}()]/g, ''))
  return { name, args, error: null }
}

export function suggestCommands(fragment) {
  const frag = String(fragment ?? '').toLowerCase()
  if (!frag.startsWith('/')) return []
  const term = frag.slice(1)
  const pool = new Set([...commandNames(), ...Object.keys(ALIASES)])
  return [...pool].filter((c) => c.startsWith(term) && c !== term).sort()
}

export function completeInput(currentInput) {
  const matches = suggestCommands(currentInput)
  if (matches.length === 0) return { input: currentInput, matches }
  if (matches.length === 1) {
    return { input: `/${matches[0]} `, matches }
  }
  return { input: currentInput, matches }
}

function line(text, tone = 'out') {
  return { text, tone }
}

function okBanner(title) {
  return [
    line('   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'dim'),
    line(`   ${title}`, 'info'),
    line('   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'dim'),
  ]
}

function describeError(res) {
  if (res.kind === 'timeout') return line(`   ⏱️ ${res.detail}`, 'err')
  if (res.kind === 'network') return line(`   🔌 Backend unreachable: ${res.detail}`, 'err')
  if (res.kind === 'invalid-path') return line(`   ⛔ ${res.detail}`, 'err')
  const detail = res.data?.detail || res.data?.raw || `HTTP ${res.status}`
  if (res.status === 401) return line('   🔒 Unauthorized — please sign in again.', 'err')
  if (res.status === 429) return line(`   🚦 Rate limited: ${detail}`, 'warn')
  return line(`   ❌ Backend error ${res.status}: ${detail}`, 'err')
}

// ---------------------------------------------------------------------------
// Local commands
// ---------------------------------------------------------------------------

registerCommand({
  name: 'help',
  aliases: ['h', '?'],
  description: 'Display available commands',
  usage: '/help',
  run() {
    const lines = [...HELP_HEADER]
    for (const name of commandNames()) {
      const cmd = getCommand(name)
      const alias = cmd.aliases?.length ? ` (aka: ${cmd.aliases.map((a) => `/${a}`).join(', ')})` : ''
      lines.push(line(`   /${name.padEnd(9)} - ${cmd.description}${alias}`, 'out'))
    }
    lines.push(...HELP_FOOTER)
    return { lines }
  },
})

registerCommand({
  name: 'clear',
  aliases: ['cls'],
  description: 'Flush the terminal buffer',
  usage: '/clear',
  run(ctx) {
    ctx.clear()
    return { lines: [line('   🧹 Terminal buffer flushed.', 'ok')] }
  },
})

registerCommand({
  name: 'echo',
  description: 'Print a message back',
  usage: '/echo [text]',
  validate(args) {
    if (args.length === 0) return 'Usage: /echo [text]'
    return null
  },
  run({ args }) {
    return { lines: [line(`   📢 ${args.join(' ')}`)] }
  },
})

registerCommand({
  name: 'date',
  description: 'Show current date and time',
  usage: '/date',
  run() {
    return { lines: [line(`   📅 ${new Date().toLocaleString()}`)] }
  },
})

registerCommand({
  name: 'uptime',
  description: 'Show session uptime',
  usage: '/uptime',
  run() {
    const uptime = Math.floor(performance.now() / 1000)
    const h = Math.floor(uptime / 3600)
    const m = Math.floor((uptime % 3600) / 60)
    const s = uptime % 60
    return { lines: [line(`   ⏱️ Session uptime: ${h}h ${m}m ${s}s`)] }
  },
})

registerCommand({
  name: 'ping',
  description: 'Measure backend round-trip time',
  usage: '/ping',
  async run() {
    const start = performance.now()
    const res = await apiRequest({ path: '/health', timeoutMs: 5000 })
    if (!res.ok) return { lines: [line('   🏓 PING failed:', 'err'), describeError(res)], failure: true }
    const ms = Math.round(performance.now() - start)
    const grade = ms < 50 ? '🟢 Fast' : ms < 200 ? '🟡 Moderate' : '🔴 Slow'
    return { lines: [line(`   🏓 PING response: ${ms}ms (${grade}) — backend ${res.data?.status || 'unknown'}`)] }
  },
})

registerCommand({
  name: 'whoami',
  description: 'Display current user identity',
  usage: '/whoami',
  run(ctx) {
    return { lines: [line(`   👤 Current user: ${ctx.userEmail || 'Anonymous'}`)] }
  },
})

registerCommand({
  name: 'identity',
  description: 'Display logged-in node signature',
  usage: '/identity',
  run(ctx) {
    return {
      lines: [
        ...okBanner('🔐  USER IDENTITY SIGNATURE'),
        line(`   USER:     ${ctx.userEmail || 'Not logged in'}`),
        line('   ROLE:     🚀 USER (authenticated via Supabase)'),
        line(`   STATUS:   ${ctx.userEmail ? '🟢 ACTIVE' : '🔴 OFFLINE'}`),
        line('   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'dim'),
      ],
    }
  },
})

registerCommand({
  name: 'matrix',
  description: 'Visual overload sequence (for fun)',
  usage: '/matrix',
  run() {
    return {
      lines: [
        ...okBanner('🟢  MATRIX VISUAL OVERLOAD SEQUENCE INITIATED'),
        line('   01000101 01011000 01000101 01000011 01010101 01000101', 'dim'),
        line('   🔓 SYSTEM SECURITY COMPROMISED... Just kidding!'),
        line('   ✨ Your ASTRAVOX setup looks absolutely incredible!', 'ok'),
        line('   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'dim'),
      ],
    }
  },
})

// ---------------------------------------------------------------------------
// Backend-backed commands (real endpoints, no simulation)
// ---------------------------------------------------------------------------

registerCommand({
  name: 'status',
  aliases: ['s'],
  description: 'Fetch system diagnostics from the backend',
  usage: '/status',
  async run(ctx) {
    const res = await apiRequest({ path: '/api/status' })
    if (!res.ok) return { lines: [describeError(res)], failure: true }
    const d = res.data || {}
    const online = typeof navigator !== 'undefined' ? navigator.onLine : true
    return {
      lines: [
        ...okBanner('📊  SYSTEM STATUS REPORT (live)'),
        line(`   [CORE]    API: ${d.status || 'unknown'} · ${d.service || 'n/a'} v${d.version || '?'}`),
        line(`   [NET]     Browser network: ${online ? '🟢 Online' : '🔴 Offline'}`),
        line(`   [DATA]    Active Database Rows: ${ctx.totalItems || 0} rows mapped`),
        line(`   [SESSION] ${ctx.userEmail || 'No active link identity found.'}`),
        line(`   [API]     ${API_BASE_URL}`),
        line(`   [TIME]    ${d.timestamp || new Date().toISOString()}`),
        line('   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'dim'),
      ],
      data: d,
    }
  },
})

registerCommand({
  name: 'stats',
  aliases: ['stat', 'st'],
  description: 'Fetch your account statistics (auth required)',
  usage: '/stats',
  async run() {
    const res = await apiRequest({ path: '/api/stats' })
    if (!res.ok) return { lines: [describeError(res)], failure: true }
    const s = res.data?.stats || {}
    return {
      lines: [
        ...okBanner('📈  ACCOUNT STATISTICS (live)'),
        line(`   [CONVERSATIONS] ${s.total_conversations ?? 0}`),
        line(`   [MEMORY ENTRIES] ${s.total_memory_entries ?? 0}`),
        line(`   [TIER]           ${s.user_tier || 'free'}`),
        line(`   [MEMBER SINCE]   ${s.created_at || 'unknown'}`),
        line('   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'dim'),
      ],
      data: s,
    }
  },
})

registerCommand({
  name: 'health',
  aliases: ['hp'],
  description: 'Backend health check (public endpoint)',
  usage: '/health',
  async run() {
    const res = await apiRequest({ path: '/health', timeoutMs: 5000 })
    if (!res.ok) return { lines: [describeError(res)], failure: true }
    const d = res.data || {}
    return { lines: [line(`   🩺 Backend health: ${d.status || 'unknown'} — ${d.service || 'n/a'} v${d.version || '?'}`, 'ok')], data: d }
  },
})

registerCommand({
  name: 'memory',
  aliases: ['mem'],
  description: 'Show your persisted memory entries (auth required)',
  usage: '/memory [count]',
  validate(args) {
    if (args.length && (!/^\d+$/.test(args[0]) || Number(args[0]) < 1 || Number(args[0]) > 200)) {
      return 'Argument must be a count between 1 and 200'
    }
    return null
  },
  async run(args) {
    const limit = args.args?.[0] ? Number(args.args[0]) : 10
    const res = await apiRequest({ path: `/api/memory?limit=${limit}` })
    if (!res.ok) return { lines: [describeError(res)], failure: true }
    const entries = res.data?.memory || []
    if (entries.length === 0) return { lines: [line('   🧠 Memory cloud is empty — nothing persisted yet.', 'warn')], data: entries }
    return {
      lines: [
        ...okBanner(`🧠  MEMORY SYSTEM (last ${entries.length} entries)`),
        ...entries.slice(0, 10).map((m) =>
          line(`   [${(m.created_at || '').slice(0, 10)}] (prio ${m.importance ?? 1}) ${String(m.content || '').slice(0, 60)}`),
        ),
        ...(entries.length > 10 ? [line(`   … and ${entries.length - 10} more`, 'dim')] : []),
        line('   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'dim'),
      ],
      data: entries,
    }
  },
})

registerCommand({
  name: 'inject',
  description: 'Persist a memory entry into the backend (auth required)',
  usage: '/inject [text]',
  validate(args) {
    if (args.length === 0) return 'Usage: /inject [text] — nothing was injected'
    if (args.join(' ').length > 500) return 'Injection payload too long (max 500 characters)'
    return null
  },
  async run(args) {
    const content = (args.args || []).join(' ')
    const res = await apiRequest({ method: 'POST', path: '/api/terminal/inject', body: { content } })
    if (!res.ok) return { lines: [line('   💉 Injection failed.', 'err'), describeError(res)], failure: true }
    const entry = res.data?.memory
    return {
      lines: [
        line('   💉 INJECTION SEQUENCE COMPLETE', 'ok'),
        line(`   📦 Persisted memory entry ${entry?.id ?? '(saved)'}: "${String(entry?.content || content).slice(0, 80)}"`),
        line('   ✅ Neural pathways updated (stored in ai_memory).', 'ok'),
      ],
      data: entry,
    }
  },
})

registerCommand({
  name: 'purge',
  description: 'Delete ALL your memory entries from the backend (auth required, destructive)',
  usage: '/purge',
  async run() {
    const res = await apiRequest({ method: 'POST', path: '/api/terminal/purge' })
    if (!res.ok) return { lines: [line('   🗑️ Purge failed.', 'err'), describeError(res)], failure: true }
    return {
      lines: [
        line('   🗑️ PURGE SEQUENCE COMPLETE', 'ok'),
        line(`   🧹 Deleted ${res.data?.deleted ?? 0} memory fragment(s).`),
        line('   ✅ Memory cloud flushed.', 'ok'),
      ],
      data: res.data,
    }
  },
})

registerCommand({
  name: 'usage',
  aliases: ['u'],
  description: 'Show your daily AI usage quota (auth required)',
  usage: '/usage',
  async run() {
    const res = await apiRequest({ path: '/api/terminal/usage' })
    if (!res.ok) return { lines: [describeError(res)], failure: true }
    const d = res.data || {}
    const used = d.used ?? 0
    const limit = d.limit ?? 0
    const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0
    const bar = '█'.repeat(Math.round(pct / 10)) + '░'.repeat(10 - Math.round(pct / 10))
    const tone = pct >= 90 ? 'err' : pct >= 70 ? 'warn' : 'ok'
    return {
      lines: [
        ...okBanner('📶  DAILY USAGE'),
        line(`   [TODAY]  ${used} / ${limit} AI requests`),
        line(`   [BAR]    ${bar} ${pct}%`, tone),
        line(`   [RESETS] ${d.resets || 'daily (UTC)'}`),
        line('   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'dim'),
      ],
      data: d,
    }
  },
})

registerCommand({
  name: 'api',
  aliases: ['version', 'ver'],
  description: 'Call any GET endpoint, e.g. /api /health or /api /api/status',
  usage: '/api [endpoint]',
  validate(args) {
    if (args.length === 0) return 'Usage: /api [endpoint] — e.g. /api /health'
    return null
  },
  async run(args) {
    const endpoint = (args.args || []).join('')
    const res = await apiRequest({ path: endpoint })
    if (!res.ok) return { lines: [line(`   📡 GET ${endpoint}`, 'info'), describeError(res)], failure: true }
    return {
      lines: [
        line(`   📡 GET ${endpoint} → ${res.status} OK`, 'ok'),
        line(`   ${JSON.stringify(res.data).slice(0, 500)}`, 'dim'),
      ],
      data: res.data,
    }
  },
})

// ---------------------------------------------------------------------------
// Executor
// ---------------------------------------------------------------------------

/**
 * Execute a raw input line against the command registry.
 * Returns { lines, ok, command, failure }.
 * `ctx` = { userEmail, totalItems, clear }.
 */
export async function executeCommand(rawInput, ctx = {}) {
  const parsed = parseCommand(rawInput)
  if (parsed.error) {
    return {
      ok: false,
      command: null,
      failure: true,
      lines: [
        line(`   ❌ ${parsed.error}`, 'err'),
        line('   💡 Type /help for a full list of available commands.', 'warn'),
      ],
    }
  }
  if (!parsed.name) return { ok: true, command: null, lines: [] }

  const cmd = getCommand(parsed.name)
  if (!cmd) {
    const suggestions = suggestCommands(`/${parsed.name}`).slice(0, 5)
    return {
      ok: false,
      command: parsed.name,
      failure: true,
      lines: [
        line(`   ❌ Unknown command: /${parsed.name}`, 'err'),
        ...(suggestions.length ? [line(`   🤔 Did you mean: ${suggestions.map((s) => `/${s}`).join(', ')}?`, 'warn')] : []),
        line('   💡 Type /help for a full list of available commands.', 'warn'),
      ],
    }
  }

  if (typeof cmd.validate === 'function') {
    const validationError = cmd.validate(parsed.args)
    if (validationError) {
      return {
        ok: false,
        command: cmd.name,
        failure: true,
        lines: [line(`   ❌ Invalid arguments: ${validationError}`, 'err')],
      }
    }
  }

  try {
    const result = await cmd.run({ args: parsed.args, ...ctx })
    return { ok: !result.failure, command: cmd.name, failure: !!result.failure, lines: result.lines || [], data: result.data }
  } catch (error) {
    return {
      ok: false,
      command: cmd.name,
      failure: true,
      lines: [line(`   ❌ Command crashed: ${error?.message || 'unexpected error'}`, 'err')],
    }
  }
}
