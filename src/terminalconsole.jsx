import { useState } from 'react'

const COMMAND_RESPONSES = {
  '/help': 'Commands: /help, /status, /clear',
  '/status': 'Astrovox workspace services are available.',
}

export default function TerminalConsole({ userEmail, totalItems, history, setHistory }) {
  const [command, setCommand] = useState('')

  function submitCommand(event) {
    event.preventDefault()
    const normalized = command.trim().toLowerCase()
    if (!normalized) return

    if (normalized === '/clear') {
      setHistory([])
    } else {
      const response = COMMAND_RESPONSES[normalized] || `Unknown command: ${normalized}. Use /help.`
      setHistory(previous => [...previous, `> ${normalized}`, response])
    }
    setCommand('')
  }

  return (
    <section style={{
      flex: 1,
      minHeight: 0,
      display: 'flex',
      flexDirection: 'column',
      border: '1px solid #1e293b',
      borderRadius: '12px',
      overflow: 'hidden',
      backgroundColor: '#02040a'
    }} aria-label="Workspace command console">
      <header style={{ padding: '12px 16px', borderBottom: '1px solid #1e293b', color: '#67e8f9', fontSize: '12px' }}>
        COMMAND CONSOLE · {userEmail} · {totalItems} CONVERSATIONS
      </header>
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px', color: '#94a3b8', fontFamily: 'monospace', fontSize: '12px' }}>
        {history.map((entry, index) => <div key={`${entry}-${index}`}>{entry}</div>)}
      </div>
      <form onSubmit={submitCommand} style={{ display: 'flex', padding: '12px', borderTop: '1px solid #1e293b' }}>
        <label htmlFor="console-command" style={{ color: '#34d399', marginRight: '8px' }}>&gt;</label>
        <input
          id="console-command"
          value={command}
          onChange={event => setCommand(event.target.value)}
          placeholder="Enter /help"
          style={{ flex: 1, border: 0, outline: 0, background: 'transparent', color: '#e2e8f0', fontFamily: 'monospace' }}
        />
      </form>
    </section>
  )
}
