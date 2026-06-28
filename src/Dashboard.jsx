import { useState, useEffect } from 'react'
import { supabase } from './supabase'
import Sidebar from './Sidebar'
import Chat from './Chat'
import Telemetry from './telemetry'
import TerminalConsole from './terminalconsole'
import MemoryPanel from './MemoryPanel'
import SettingsPanel from './SettingsPanel'

export default function Dashboard({ session }) {
  const [currentConversationId, setCurrentConversationId] = useState(null)
  const [terminalLogs, setTerminalLogs] = useState([
    '>> ASTROVOX OS v2.0.6 INITIALIZED SUCCESS',
    '>> Type /help to list available mainframe overrides.'
  ])
  const [totalConversations, setTotalConversations] = useState(0)
  const [dbStatus, setDbStatus] = useState('online')
  const [activePanel, setActivePanel] = useState('chat') // 'chat', 'memory', 'settings'

  useEffect(() => {
    if (session) {
      loadUserStats()
    }
  }, [session])

  async function loadUserStats() {
    try {
      const { count, error } = await supabase
        .from('conversations')
        .select('*', { count: 'exact', head: true })
        .eq('user_id', session.user.id)
        .eq('is_deleted', false)

      if (error) throw error
      setTotalConversations(count || 0)
      setDbStatus('online')
    } catch (err) {
      console.error('Failed to load stats:', err)
      setDbStatus('offline')
    }
  }

  const pushSystemLog = (message) => {
    const timestamp = new Date().toLocaleTimeString()
    setTerminalLogs(prev => [...prev, `[${timestamp}] ${message}`])
  }

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      backgroundColor: '#02040a',
      color: '#e2e8f0',
      fontFamily: "'Inter', 'Segoe UI', monospace",
      backgroundImage: 'radial-gradient(ellipse at 50% 0%, rgba(6, 182, 212, 0.05) 0%, transparent 70%)'
    }}>
      {/* Sidebar */}
      <Sidebar
        session={session}
        onSelectConversation={setCurrentConversationId}
        currentConversationId={currentConversationId}
      />

      {/* Main Content */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}>
        {/* Top Header */}
        <header style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: 'rgba(4, 8, 20, 0.7)',
          backdropFilter: 'blur(12px)',
          border: '1px solid #1e293b',
          borderRadius: '0 0 16px 0',
          padding: '16px 24px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.4)'
        }}>
          <div>
            <h2 style={{
              margin: 0,
              fontSize: '18px',
              letterSpacing: '1px',
              background: 'linear-gradient(135deg, #67e8f9, #06b6d4)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              color: 'transparent'
            }}>
              🛸 ASTRAVOX // MAIN FRAME
            </h2>
            <p style={{ margin: '4px 0 0 0', fontSize: '10px', color: '#64748b' }}>
              OPERATOR: <span style={{ color: '#f472b6' }}>{session.user.email}</span>
              <span style={{ marginLeft: '16px' }}>
                <span style={{ color: '#34d399' }}>●</span> {dbStatus}
              </span>
            </p>
          </div>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <button
              onClick={() => setActivePanel('chat')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'chat' ? '#06b6d4' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'chat' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              💬 CHAT
            </button>
            <button
              onClick={() => setActivePanel('memory')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'memory' ? '#06b6d4' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'memory' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              🧠 MEMORY
            </button>
            <button
              onClick={() => setActivePanel('settings')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'settings' ? '#06b6d4' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'settings' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              ⚙️ SETTINGS
            </button>
            <button
              onClick={() => supabase.auth.signOut()}
              style={{
                padding: '8px 20px',
                backgroundColor: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid #ef4444',
                color: '#f87171',
                borderRadius: '40px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s',
                letterSpacing: '0.5px'
              }}
              onMouseEnter={(e) => {
                e.target.style.backgroundColor = 'rgba(239, 68, 68, 0.25)'
                e.target.style.transform = 'scale(1.02)'
              }}
              onMouseLeave={(e) => {
                e.target.style.backgroundColor = 'rgba(239, 68, 68, 0.15)'
                e.target.style.transform = 'scale(1)'
              }}
            >
              DISCONNECT
            </button>
          </div>
        </header>

        {/* Main Content Area */}
        <div style={{
          flex: 1,
          display: 'grid',
          gridTemplateColumns: activePanel === 'chat' ? '1fr 1fr' : '1fr',
          gap: '16px',
          padding: '16px',
          overflow: 'hidden'
        }}>
          {/* Left Panel */}
          {activePanel === 'chat' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <Chat
                session={session}
                conversationId={currentConversationId}
                onConversationChange={(id) => setCurrentConversationId(id)}
              />
            </div>
          )}

          {activePanel === 'memory' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <MemoryPanel session={session} />
            </div>
          )}

          {activePanel === 'settings' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <SettingsPanel session={session} />
            </div>
          )}

          {/* Right Panel: Terminal & Telemetry (only in chat mode) */}
          {activePanel === 'chat' && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
              overflow: 'hidden'
            }}>
              <TerminalConsole
                userEmail={session.user.email}
                totalItems={totalConversations}
                history={terminalLogs}
                setHistory={setTerminalLogs}
              />
              <Telemetry
                totalPackets={totalConversations}
                dbStatus={dbStatus}
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          paddingTop: '16px',
          borderTop: '1px solid #1e293b',
          textAlign: 'center',
          fontSize: '10px',
          color: '#475569',
          letterSpacing: '0.5px',
          padding: '16px'
        }}>
          ASTRAVOX PRIME v2.0.6 · Built by Prabesh Paudel, Dipson Baral & Susanta AI
          <span style={{ margin: '0 12px' }}>|</span>
          <span style={{ color: '#334155' }}>SYSTEM STATUS: {dbStatus === 'online' ? '🟢 OPERATIONAL' : '⚠️ DEGRADED'}</span>
        </div>
      </div>
    </div>
  )
}
