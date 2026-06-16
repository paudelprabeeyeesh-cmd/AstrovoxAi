import { useEffect, useState } from 'react'
import { supabase } from './supabase'
import Auth from './auth'
import Telemetry from './telemetry'
import TerminalConsole from './terminalconsole'

function App() {
  const [session, setSession] = useState(null)
  const [data, setData] = useState([])
  const [newItem, setNewItem] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [connectionStatus, setConnectionStatus] = useState('online')
  const [currentTime, setCurrentTime] = useState(new Date())

  // 🛰️ CENTRAL TERMINAL LOG STREAM
  const [terminalLogs, setTerminalLogs] = useState([
    '>> ASTROVOX OS v2.0.6 INITIALIZED SUCCESS',
    '>> Type /help to list available mainframe overrides.'
  ])

  const pushSystemLog = (message) => {
    const timestamp = new Date().toLocaleTimeString()
    setTerminalLogs(prev => [...prev, `[${timestamp}] ${message}`])
  }

  // Live clock
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  // Auth session
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })

    return () => subscription.unsubscribe()
  }, [])

  async function fetchData() {
    if (!session) return
    try {
      setLoading(true)
      const { data: tableData, error: fetchError } = await supabase
        .from('todos')
        .select('*')
        .order('id', { ascending: false })

      if (fetchError) throw fetchError
      setData(tableData)
      pushSystemLog('>> Cloud sync finalized. Data packets retrieved.')
    } catch (err) {
      setError(err.message)
      pushSystemLog(`>> ERROR: Failed matrix fetch sequence: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (session) {
      pushSystemLog(`>> Operator session validated for link: ${session.user.email}`)
      fetchData()
    }
  }, [session])

  async function handleAddItem(e) {
    e.preventDefault()
    if (!newItem.trim()) return

    try {
      pushSystemLog(`>> Initializing injection sequence for packet: "${newItem}"...`)
      const { data: insertedData, error: insertError } = await supabase
        .from('todos')
        .insert([{ title: newItem }])
        .select()

      if (insertError) throw insertError
      setData([insertedData[0], ...data])
      setNewItem('')
      pushSystemLog(`>> SUCCESS: Packet stored in remote cloud register.`)
    } catch (err) {
      alert('Transmission Failure: ' + err.message)
      pushSystemLog(`>> CRITICAL: Injection failed. Pipeline broken.`)
    }
  }

  async function handleDeleteItem(id) {
    try {
      pushSystemLog(`>> Deploying data purge vectors for hex ID: [${id}]...`)
      const { error: deleteError } = await supabase
        .from('todos')
        .delete()
        .eq('id', id)

      if (deleteError) throw deleteError
      setData(data.filter(item => item.id !== id))
      pushSystemLog(`>> SUCCESS: Target hex data completely vaporized from cloud.`)
    } catch (err) {
      alert('Purge Error: ' + err.message)
      pushSystemLog(`>> CRITICAL: Purge override rejected by remote database.`)
    }
  }

  if (!session) {
    return <Auth />
  }

  // Calculate metrics
  const totalEntries = data.length
  const lastEntry = data.length > 0 ? data[0] : null

  return (
    <div style={{
      backgroundColor: '#02040a',
      minHeight: '100vh',
      color: '#e2e8f0',
      fontFamily: "'Inter', 'Segoe UI', monospace",
      padding: '24px 16px',
      backgroundImage: 'radial-gradient(ellipse at 50% 0%, rgba(6, 182, 212, 0.05) 0%, transparent 70%)'
    }}>
      <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
        
        {/* ========== TOP HEADER WITH GLASS ========== */}
        <header style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: 'rgba(4, 8, 20, 0.7)',
          backdropFilter: 'blur(12px)',
          border: '1px solid #1e293b',
          borderRadius: '16px',
          padding: '16px 24px',
          marginBottom: '28px',
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
                <span style={{ color: '#34d399' }}>●</span> {connectionStatus}
              </span>
              <span style={{ marginLeft: '16px', color: '#475569' }}>
                {currentTime.toLocaleTimeString()}
              </span>
            </p>
          </div>
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
            onMouseEnter={(e) => { e.target.style.backgroundColor = 'rgba(239, 68, 68, 0.25)'; e.target.style.transform = 'scale(1.02)' }}
            onMouseLeave={(e) => { e.target.style.backgroundColor = 'rgba(239, 68, 68, 0.15)'; e.target.style.transform = 'scale(1)' }}
          >
            DISCONNECT
          </button>
        </header>

        {/* ========== STATS ROW ========== */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
          gap: '16px',
          marginBottom: '24px'
        }}>
          <div style={{
            background: 'rgba(4,8,20,0.5)',
            backdropFilter: 'blur(8px)',
            border: '1px solid #1e293b',
            borderRadius: '12px',
            padding: '14px 16px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '10px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '1px' }}>Total Packets</div>
            <div style={{ fontSize: '28px', fontWeight: '700', color: '#67e8f9' }}>{totalEntries}</div>
          </div>
          <div style={{
            background: 'rgba(4,8,20,0.5)',
            backdropFilter: 'blur(8px)',
            border: '1px solid #1e293b',
            borderRadius: '12px',
            padding: '14px 16px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '10px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '1px' }}>Last Injected</div>
            <div style={{ fontSize: '16px', fontWeight: '500', color: '#cbd5e1' }}>
              {lastEntry ? lastEntry.title || '—' : '—'}
            </div>
          </div>
          <div style={{
            background: 'rgba(4,8,20,0.5)',
            backdropFilter: 'blur(8px)',
            border: '1px solid #1e293b',
            borderRadius: '12px',
            padding: '14px 16px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '10px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '1px' }}>Cloud Status</div>
            <div style={{ fontSize: '18px', fontWeight: '600', color: error ? '#ef4444' : '#34d399' }}>
              {error ? '⚠️ OFFLINE' : '🟢 ONLINE'}
            </div>
          </div>
        </div>

        {/* ========== COMMAND LINE FORM ========== */}
        <form onSubmit={handleAddItem} style={{
          display: 'flex',
          gap: '12px',
          marginBottom: '30px',
          alignItems: 'stretch'
        }}>
          <input 
            type="text" 
            placeholder="Inject new data packet into cloud core..." 
            value={newItem}
            onChange={(e) => setNewItem(e.target.value)}
            style={{
              flex: 1,
              padding: '14px 20px',
              borderRadius: '40px',
              backgroundColor: 'rgba(4,8,20,0.6)',
              border: '1px solid #1e293b',
              color: '#fff',
              fontFamily: 'monospace',
              fontSize: '13px',
              outline: 'none',
              transition: 'border-color 0.2s'
            }}
            onFocus={(e) => e.target.style.borderColor = '#06b6d4'}
            onBlur={(e) => e.target.style.borderColor = '#1e293b'}
          />
          <button type="submit" style={{
            padding: '0 32px',
            backgroundColor: '#06b6d4',
            color: '#02040a',
            border: 'none',
            borderRadius: '40px',
            cursor: 'pointer',
            fontWeight: '700',
            fontSize: '13px',
            letterSpacing: '0.5px',
            transition: 'all 0.2s'
          }}
          onMouseEnter={(e) => { e.target.style.transform = 'scale(1.02)'; e.target.style.boxShadow = '0 0 20px rgba(6,182,212,0.4)' }}
          onMouseLeave={(e) => { e.target.style.transform = 'scale(1)'; e.target.style.boxShadow = 'none' }}
          >
            INJECT
          </button>
        </form>

        <hr style={{ borderColor: '#1e293b', margin: '30px 0' }} />

        {/* ========== DATA LIST ========== */}
        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: '#06b6d4', fontSize: '13px' }}>
            <span style={{ display: 'inline-block', width: '16px', height: '16px', border: '2px solid #06b6d4', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }}></span>
            Scanning cloud matrices...
          </div>
        )}
        {error && (
          <div style={{ background: 'rgba(239,68,68,0.1)', borderLeft: '4px solid #ef4444', padding: '12px 16px', borderRadius: '8px', color: '#fca5a5', fontSize: '13px' }}>
            ⚠️ ERROR ARCHITECTURE: {error}
          </div>
        )}
        {!loading && data.length === 0 && (
          <p style={{ color: '#64748b', fontSize: '13px', textAlign: 'center', padding: '20px' }}>
            Core memory bank registers as completely blank.
          </p>
        )}

        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {data.map((item) => (
            <li key={item.id} style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '14px 20px',
              backgroundColor: 'rgba(4, 8, 20, 0.4)',
              borderRadius: '12px',
              marginBottom: '10px',
              border: '1px solid #1e293b',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.borderColor = '#334155'}
            onMouseLeave={(e) => e.currentTarget.style.borderColor = '#1e293b'}
            >
              <span style={{ fontSize: '13px', color: '#cbd5e1' }}>
                {item.title || JSON.stringify(item)}
                <span style={{ fontSize: '10px', color: '#475569', marginLeft: '12px' }}>
                  {new Date(item.created_at).toLocaleTimeString()}
                </span>
              </span>
              <button 
                onClick={() => handleDeleteItem(item.id)}
                style={{
                  backgroundColor: 'transparent',
                  border: '1px solid #334155',
                  color: '#94a3b8',
                  padding: '6px 14px',
                  borderRadius: '40px',
                  cursor: 'pointer',
                  fontSize: '10px',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => { e.target.style.borderColor = '#ef4444'; e.target.style.color = '#f87171' }}
                onMouseLeave={(e) => { e.target.style.borderColor = '#334155'; e.target.style.color = '#94a3b8' }}
              >
                PURGE
              </button>
            </li>
          ))}
        </ul>

        {/* ========== TERMINAL & TELEMETRY ========== */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '20px',
          marginTop: '30px'
        }}>
          <TerminalConsole 
            userEmail={session.user.email} 
            totalItems={data.length} 
            history={terminalLogs}
            setHistory={setTerminalLogs}
          />
          <Telemetry 
            totalPackets={data.length} 
            dbStatus={error ? 'offline' : 'online'} 
          />
        </div>

        {/* ========== FOOTER ========== */}
        <div style={{
          marginTop: '40px',
          paddingTop: '16px',
          borderTop: '1px solid #1e293b',
          textAlign: 'center',
          fontSize: '10px',
          color: '#475569',
          letterSpacing: '0.5px'
        }}>
          ASTRAVOX PRIME v2.0.6 · Built by Prabesh Paudel, Dipson Baral & Susanta AI
          <span style={{ margin: '0 12px' }}>|</span>
          <span style={{ color: '#334155' }}>SYSTEM STATUS: {error ? '⚠️ DEGRADED' : '🟢 OPERATIONAL'}</span>
        </div>
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

export default App