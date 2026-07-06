import { useState, useRef, useEffect } from 'react'

export default function TerminalConsole({ userEmail, totalItems }) {
  const [input, setInput] = useState('')
  const [history, setHistory] = useState([
    '╔═══════════════════════════════════════════════════════════════╗',
    '║   🚀 ASTROVOX OS v2.0.6 — SOVEREIGN TERMINAL INITIALIZED   ║',
    '║   ═══════════════════════════════════════════════════════════  ║',
    '║   Type /help to list available mainframe overrides.          ║',
    '╚═══════════════════════════════════════════════════════════════╝'
  ])
  const terminalEndRef = useRef(null)

  // Auto-scroll terminal when new text prints
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history])

  const handleCommandSubmit = (e) => {
    e.preventDefault()
    const cmd = input.trim().toLowerCase()
    if (!cmd) return

    let response = []
    const timestamp = new Date().toLocaleTimeString()
    
    // Add user command with timestamp
    response.push(`[${timestamp}] guest@astrovox:~# ${input}`)

    switch (cmd) {
      case '/help':
        response.push(
          '   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
          '   📟  AVAILABLE COMMANDS:',
          '   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
          '   /status   - Fetch system architecture diagnostics',
          '   /identity - Display logged-in node signatures',
          '   /clear    - Flush the current terminal buffer',
          '   /matrix   - Execute visual style overload test',
          '   /whoami   - Display current user identity',
          '   /ping     - Test system response time',
          '   /echo [text] - Print custom message',
          '   /date     - Show current date and time',
          '   /uptime   - Show system uptime',
          '   /inject   - Simulate data injection',
          '   /purge    - Simulate data purge',
          '   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
        )
        break

      case '/status':
        response.push(
          '   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
          '   📊  SYSTEM STATUS REPORT',
          '   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
          `   [CORE]    Memory Cloud Stack: ${navigator.onLine ? '🟢 Online' : '🔴 Offline'}`,
          `   [DATA]    Active Database Rows: ${totalItems || 0} rows mapped`,
          `   [RAM]     Hardware Profile: 4.0 GB SODIMM Architecture Detected`,
          `   [GPU]     WebGL: ${document.createElement('canvas').getContext('webgl') ? '✅ Supported' : '❌ Not Available'}`,
          `   [UPTIME]  ${Math.floor(performance.now() / 1000)} seconds`,
          `   [SESSION] ${userEmail || 'No active link identity found.'}`,
          '   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
        )
        break

      case '/identity':
        response.push(
          '   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
          '   🔐  USER IDENTITY SIGNATURE',
          '   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
          `   USER:     ${userEmail || 'Not logged in'}`,
          `   ROLE:     ${userEmail === 'admin@astravox.ai' ? '🛡️ ADMINISTRATOR' : '🚀 USER'}`,
          `   STATUS:   ${userEmail ? '🟢 ACTIVE' : '🔴 OFFLINE'}`,
          '   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
        )
        break

      case '/whoami':
        response.push(
          `   👤 Current user: ${userEmail || 'Anonymous'}`
        )
        break

      case '/ping': {
        const pingTime = Math.floor(Math.random() * 30 + 5)
        response.push(
          `   🏓 PING response: ${pingTime}ms (${pingTime < 15 ? '🟢 Fast' : pingTime < 25 ? '🟡 Moderate' : '🔴 Slow'})`
        )
        break
      }

      case '/date':
        response.push(
          `   📅 ${new Date().toLocaleString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })}`
        )
        break

      case '/uptime': {
        const uptime = Math.floor(performance.now() / 1000)
        const h = Math.floor(uptime / 3600)
        const m = Math.floor((uptime % 3600) / 60)
        const s = uptime % 60
        response.push(
          `   ⏱️ System Uptime: ${h}h ${m}m ${s}s`
        )
        break
      }

      case '/matrix':
        response.push(
          '   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
          '   🟢  MATRIX VISUAL OVERLOAD SEQUENCE INITIATED',
          '   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
          '   01000101 01011000 01000101 01000011 01010101 01010100 01000101',
          '   01010011 01011001 01010011 01010100 01000101 01001101 01010011',
          '   01001111 01001110 01001100 01001001 01001110 01000101 00100000',
          '   01010011 01000101 01000011 01010101 01010010 01000101 01000100',
          '   ═══════════════════════════════════════════════════════════',
          '   🔓 SYSTEM SECURITY COMPROMISED... Just kidding!',
          '   ✨ Your ASTRAVOX setup looks absolutely incredible!',
          '   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
        )
        break

      case '/clear':
        setHistory([])
        setInput('')
        return

      case '/inject':
        response.push(
          '   💉 INJECTION SEQUENCE INITIATED',
          `   📦 Injecting ${Math.floor(Math.random() * 1000 + 100)} packets into neural core...`,
          '   ✅ Data injection complete. Neural pathways updated.'
        )
        break

      case '/purge':
        response.push(
          '   🗑️ PURGE SEQUENCE INITIATED',
          `   🧹 Clearing ${Math.floor(Math.random() * 50 + 10)} memory fragments...`,
          '   ✅ Purge complete. System cache flushed.'
        )
        break

      case '/echo': {
        const echoText = input.replace('/echo', '').trim() || '...nothing to echo...'
        response.push(
          `   📢 ${echoText}`
        )
        break
      }

      default:
        // Handle custom commands as API calls
        if (cmd.startsWith('/api')) {
          response.push(
            '   🌐 API REQUEST DETECTED',
            `   📡 Simulating request to endpoint: ${cmd.replace('/api', '').trim() || '/'}`,
            '   ⏳ Processing...',
            '   ✅ Response: 200 OK — Data payload delivered.'
          )
        } else {
          response.push(
            `   ❌ bash: command not found: ${cmd}`,
            `   💡 Type /help for a full list of available commands.`
          )
        }
    }

    setHistory(prev => [...prev, ...response])
    setInput('')
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
      {/* Scanline Effect */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,255,0,0.02) 2px, rgba(0,255,0,0.02) 4px)',
        pointerEvents: 'none'
      }} />
      
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '12px',
        borderBottom: '1px solid #0f172a',
        paddingBottom: '8px'
      }}>
        <h3 style={{ 
          margin: 0, 
          fontSize: '11px', 
          color: '#64748b', 
          letterSpacing: '2px',
          textTransform: 'uppercase'
        }}>
          📟 CORE TERMINAL OVERRIDE CONSOLE
        </h3>
        <div style={{
          display: 'flex',
          gap: '6px'
        }}>
          <span style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            background: '#ef4444',
            display: 'inline-block'
          }} />
          <span style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            background: '#eab308',
            display: 'inline-block'
          }} />
          <span style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            background: '#22c55e',
            display: 'inline-block'
          }} />
        </div>
      </div>

      {/* Terminal History Display Screen */}
      <div style={{
        backgroundColor: '#040814',
        border: '1px solid #0f172a',
        borderRadius: '6px',
        padding: '14px',
        height: '180px',
        overflowY: 'auto',
        fontSize: '11px',
        color: '#34d399',
        lineHeight: '1.7',
        display: 'flex',
        flexDirection: 'column',
        gap: '2px',
        fontFamily: "'JetBrains Mono', 'Courier New', monospace"
      }}>
        {history.map((line, idx) => {
          let color = '#34d399' // default green
          if (line.startsWith('guest@astrovox')) color = '#67e8f9' // cyan
          else if (line.includes('ERROR') || line.includes('❌')) color = '#ef4444' // red
          else if (line.includes('✅') || line.includes('SUCCESS')) color = '#22c55e' // bright green
          else if (line.includes('⚠️') || line.includes('WARNING')) color = '#eab308' // yellow
          else if (line.includes('━')) color = '#1e293b' // dim separator
          else if (line.includes('╔') || line.includes('║') || line.includes('╚')) color = '#334155' // box borders
          
          return (
            <div key={idx} style={{ 
              color: color,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              fontSize: '11px'
            }}>
              {line}
            </div>
          )
        })}
        <div ref={terminalEndRef} />
      </div>

      {/* Command Line Input */}
      <form onSubmit={handleCommandSubmit} style={{ 
        display: 'flex', 
        marginTop: '10px', 
        alignItems: 'center',
        borderTop: '1px solid #0f172a',
        paddingTop: '10px'
      }}>
        <span style={{ 
          color: '#67e8f9', 
          fontSize: '12px', 
          marginRight: '10px',
          fontFamily: "'JetBrains Mono', monospace"
        }}>
          ❯
        </span>
        <input 
          type="text"
          placeholder="Enter command... (try /help)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          autoFocus
          style={{
            flex: 1,
            backgroundColor: 'transparent',
            border: 'none',
            outline: 'none',
            color: '#67e8f9',
            fontFamily: "'JetBrains Mono', 'Courier New', monospace",
            fontSize: '12px',
            padding: '4px 0',
            caretColor: '#34d399'
          }}
        />
        <span style={{ 
          color: '#334155', 
          fontSize: '9px',
          letterSpacing: '1px',
          marginLeft: '12px'
        }}>
          {input.length > 0 ? 'ACTIVE' : 'STANDBY'}
        </span>
      </form>
      
      {/* Footer Stats */}
      <div style={{
        marginTop: '8px',
        paddingTop: '8px',
        borderTop: '1px solid #0f172a',
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '9px',
        color: '#334155',
        fontFamily: "'JetBrains Mono', monospace"
      }}>
        <span>TERMINAL v2.0.6</span>
        <span>PID: {Math.floor(Math.random() * 9000 + 1000)}</span>
        <span>{history.length} lines</span>
      </div>
    </div>
  )
}