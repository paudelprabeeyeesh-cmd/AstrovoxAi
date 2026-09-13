import { useState, useRef, useEffect, useCallback } from 'react'
import { executeCommand, suggestCommands, completeInput } from './terminal/engine'
import { trackEvent } from './telemetry'

const MAX_SCROLLBACK = 500
const TONE_COLORS = {
  out: '#34d399',
  ok: '#22c55e',
  warn: '#eab308',
  err: '#ef4444',
  info: '#67e8f9',
  dim: '#334155',
}

const BANNER = [
  { text: '╔═══════════════════════════════════════════════════════════════╗', tone: 'dim' },
  { text: '║   🚀 ASTRAVOX OS v2.1.0 — SOVEREIGN TERMINAL INITIALIZED   ║', tone: 'info' },
  { text: '║   ═══════════════════════════════════════════════════════════  ║', tone: 'dim' },
  { text: '║   Live backend console. Type /help to list available commands. ║', tone: 'out' },
  { text: '╚═══════════════════════════════════════════════════════════════╝', tone: 'dim' },
]

function toneFor(line) {
  if (line.prompt) return TONE_COLORS.info
  return TONE_COLORS[line.tone] || TONE_COLORS.out
}

export default function TerminalConsole({ userEmail, totalItems }) {
  const [lines, setLines] = useState(BANNER)
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [cmdHistory, setCmdHistory] = useState([])
  const [historyIdx, setHistoryIdx] = useState(-1)
  const [suggestions, setSuggestions] = useState([])
  const terminalEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines, busy])

  const pushLines = useCallback((newLines) => {
    setLines((prev) => [...prev, ...newLines].slice(-MAX_SCROLLBACK))
  }, [])

  const clearConsole = useCallback(() => setLines([]), [])

  const handleCommandSubmit = async (e) => {
    e?.preventDefault?.()
    const raw = input.trim()
    if (!raw || busy) return

    const timestamp = new Date().toLocaleTimeString()
    const started = performance.now()

    pushLines([{ text: `[${timestamp}] guest@astrovox:~# ${raw}`, prompt: true }])
    setInput('')
    setSuggestions([])
    setCmdHistory((prev) => [...prev, raw].slice(-100))
    setHistoryIdx(-1)
    setBusy(true)

    let result
    try {
      result = await executeCommand(raw, { userEmail, totalItems, clear: clearConsole })
    } catch {
      result = { lines: [{ text: '   ❌ Unexpected terminal failure.', tone: 'err' }], failure: true, command: null }
    }
    pushLines(result.lines)
    setBusy(false)

    // Telemetry: every executed command, its duration and success/failure.
    trackEvent('terminal_command', {
      command: result.command || raw.split(/\s+/)[0].replace(/^\//, ''),
      success: !result.failure,
      failure: !!result.failure,
      duration_ms: Math.round(performance.now() - started),
    })
  }

  const copyOutput = useCallback(() => {
    const text = lines.map((l) => l.text).join('\n')
    navigator.clipboard?.writeText(text).catch(() => { })
  }, [lines])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleCommandSubmit(e)
      return
    }
    if (e.key === 'Tab') {
      e.preventDefault()
      const { input: completed, matches } = completeInput(input)
      setInput(completed)
      setSuggestions(matches)
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (cmdHistory.length === 0) return
      const next = historyIdx === -1 ? cmdHistory.length - 1 : Math.max(0, historyIdx - 1)
      setHistoryIdx(next)
      setInput(cmdHistory[next])
      return
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (historyIdx === -1) return
      const next = historyIdx + 1
      if (next >= cmdHistory.length) {
        setHistoryIdx(-1)
        setInput('')
      } else {
        setHistoryIdx(next)
        setInput(cmdHistory[next])
      }
      return
    }
    if (e.ctrlKey && !e.shiftKey && e.key.toLowerCase() === 'l') {
      e.preventDefault()
      clearConsole()
      return
    }
    if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'c') {
      e.preventDefault()
      copyOutput()
    }
  }

  return (
    <div style={{
      backgroundColor: '#02040a',
      border: '1px solid #1e293b',
      borderRadius: '12px',
      padding: '20px',
      marginTop: '20px',
      fontFamily: "'JetBrains Mono', 'Courier New', monospace",
      boxShadow: 'inset 0 0 20px rgba(0, 255, 0, 0.03)',
      position: 'relative',
      overflow: 'hidden'
    }}>
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
        background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,255,0,0.02) 2px, rgba(0,255,0,0.02) 4px)',
        pointerEvents: 'none'
      }} />

      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: '12px', borderBottom: '1px solid #0f172a', paddingBottom: '8px'
      }}>
        <h3 style={{ margin: 0, fontSize: '11px', color: '#64748b', letterSpacing: '2px', textTransform: 'uppercase' }}>
          📟 CORE TERMINAL OVERRIDE CONSOLE
        </h3>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <button onClick={copyOutput} title="Copy output (Ctrl+Shift+C)" style={btnStyle}>⧉ COPY</button>
          <button onClick={clearConsole} title="Clear console (Ctrl+L)" style={btnStyle}>✕ CLEAR</button>
          <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#ef4444', display: 'inline-block' }} />
          <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#eab308', display: 'inline-block' }} />
          <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: busy ? '#67e8f9' : '#22c55e', display: 'inline-block' }} />
        </div>
      </div>

      <div style={{
        backgroundColor: '#040814', border: '1px solid #0f172a', borderRadius: '6px',
        padding: '14px', height: '240px', overflowY: 'auto', fontSize: '11px',
        color: '#34d399', lineHeight: '1.7', display: 'flex', flexDirection: 'column', gap: '2px',
        fontFamily: "'JetBrains Mono', 'Courier New', monospace"
      }} onClick={() => inputRef.current?.focus()}>
        {lines.map((l, idx) => (
          <div key={idx} style={{ color: toneFor(l), whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: '11px' }}>
            {l.text}
          </div>
        ))}
        {busy && (
          <div style={{ color: '#67e8f9', fontSize: '11px' }}>⏳ Executing…</div>
        )}
        {suggestions.length > 1 && (
          <div style={{ color: '#475569', fontSize: '10px' }}>
            Tab: {suggestions.map((s) => `/${s}`).join('  ')}
          </div>
        )}
        <div ref={terminalEndRef} />
      </div>

      <form onSubmit={handleCommandSubmit} style={{
        display: 'flex', marginTop: '10px', alignItems: 'center',
        borderTop: '1px solid #0f172a', paddingTop: '10px'
      }}>
        <span style={{ color: '#67e8f9', fontSize: '12px', marginRight: '10px', fontFamily: "'JetBrains Mono', monospace" }}>❯</span>
        <input
          ref={inputRef}
          type="text"
          placeholder="Enter command... (try /help)"
          value={input}
          disabled={busy}
          onChange={(e) => {
            setInput(e.target.value)
            setSuggestions(suggestCommands(e.target.value))
          }}
          onKeyDown={handleKeyDown}
          autoFocus
          style={{
            flex: 1, backgroundColor: 'transparent', border: 'none', outline: 'none',
            color: '#67e8f9', fontFamily: "'JetBrains Mono', 'Courier New', monospace",
            fontSize: '12px', padding: '4px 0', caretColor: '#34d399'
          }}
        />
        <span style={{ color: '#334155', fontSize: '9px', letterSpacing: '1px', marginLeft: '12px' }}>
          {busy ? 'BUSY' : input.length > 0 ? 'ACTIVE' : 'STANDBY'}
        </span>
      </form>

      <div style={{
        marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #0f172a',
        display: 'flex', justifyContent: 'space-between', fontSize: '9px',
        color: '#334155', fontFamily: "'JetBrains Mono', monospace"
      }}>
        <span>TERMINAL v2.1.0 (LIVE)</span>
        <span>{busy ? '⏳ RUNNING' : '🟢 READY'}</span>
        <span>{lines.length} lines</span>
      </div>
    </div>
  )
}

const btnStyle = {
  background: 'transparent',
  border: '1px solid #1e293b',
  color: '#64748b',
  fontSize: '9px',
  letterSpacing: '1px',
  borderRadius: '4px',
  padding: '3px 8px',
  cursor: 'pointer',
  fontFamily: 'inherit',
}
