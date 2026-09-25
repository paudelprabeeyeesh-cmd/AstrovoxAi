import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { debugMetaReality, getUniverseMessages } from '../../services/multiverseService'

export default function MetaDebugTools({ universeId }) {
  const [debug, setDebug] = useState(null)
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    if (!universeId) return
    setLoading(true)
    Promise.all([
      debugMetaReality(universeId).catch(() => null),
      getUniverseMessages(universeId, 200, 0).catch(() => ({ messages: [] })),
    ]).then(([d, m]) => {
      setDebug(d)
      setMessages(m.messages || [])
      setError(d?.error ? d.error : null)
    }).finally(() => setLoading(false))
  }, [universeId])

  function exportJSON() {
    const payload = { debug, messages, exported_at: new Date().toISOString() }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `meta-debug-${universeId || 'unknown'}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) return <div style={{ color: '#64748b', fontSize: '12px', padding: '12px' }}>Running meta-reality analysis...</div>
  if (error) return <div style={{ color: '#f87171', fontSize: '12px', padding: '12px' }}>⚠️ {error}</div>
  if (!debug) return <div style={{ color: '#475569', fontSize: '12px', padding: '12px' }}>Select a universe to debug meta-reality</div>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '12px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h4 style={{ margin: 0, fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Meta-Reality Debugger</h4>
        <button onClick={exportJSON} style={{ padding: '4px 10px', backgroundColor: 'rgba(6,182,212,0.15)', border: '1px solid #06b6d4', borderRadius: '6px', color: '#06b6d4', cursor: 'pointer', fontSize: '10px', fontFamily: 'inherit' }}>
          Export JSON
        </button>
      </div>

      <div style={{ display: 'flex', gap: '6px' }}>
        {['overview', 'parent_chain', 'messages'].map((tab) => (
          <button key={tab} onClick={() => setActiveTab(tab)} style={{ padding: '4px 10px', backgroundColor: activeTab === tab ? '#06b6d4' : 'rgba(4,8,20,0.5)', border: `1px solid ${activeTab === tab ? '#06b6d4' : '#1e293b'}`, borderRadius: '6px', color: activeTab === tab ? '#02040a' : '#94a3b8', cursor: 'pointer', fontSize: '10px', fontFamily: 'inherit', textTransform: 'capitalize' }}>
            {tab.replace('_', ' ')}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {activeTab === 'overview' && (
          <motion.div key="overview" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
            {Object.entries({
              'Status': debug.status,
              'Generation': debug.generation,
              'Messages': debug.message_count,
              'Active Branches': debug.active_branches,
            }).map(([k, v]) => (
              <div key={k} style={{ padding: '8px', backgroundColor: 'rgba(30,41,59,0.5)', border: '1px solid #1e293b', borderRadius: '6px' }}>
                <div style={{ fontSize: '10px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{k}</div>
                <div style={{ fontSize: '14px', fontWeight: '700', color: '#67e8f9', marginTop: '4px' }}>{v}</div>
              </div>
            ))}
          </motion.div>
        )}

        {activeTab === 'parent_chain' && (
          <motion.div key="parent_chain" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {(debug.parent_chain || []).map((node, i) => (
              <div key={node.id} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '8px 10px', backgroundColor: 'rgba(30,41,59,0.5)', border: '1px solid #1e293b', borderRadius: '6px', fontSize: '11px' }}>
                <span style={{ fontSize: '10px', color: '#475569' }}>#{i}</span>
                <span style={{ color: '#cbd5e1', fontWeight: '500' }}>{node.name}</span>
                <span style={{ marginLeft: 'auto', color: '#475569', fontSize: '10px' }}>gen {node.generation}</span>
              </div>
            ))}
          </motion.div>
        )}

        {activeTab === 'messages' && (
          <motion.div key="messages" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '300px', overflowY: 'auto' }}>
            {messages.map((m, i) => (
              <div key={m.id || i} style={{ padding: '6px 10px', backgroundColor: 'rgba(30,41,59,0.3)', borderRadius: '4px', fontSize: '11px', color: '#94a3b8' }}>
                <span style={{ color: '#67e8f9', fontWeight: '600', textTransform: 'uppercase', fontSize: '10px' }}>{m.role}</span>
                <span style={{ marginLeft: '8px' }}>{m.content?.slice(0, 120)}{m.content?.length > 120 ? '...' : ''}</span>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {debug.role_distribution && (
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {Object.entries(debug.role_distribution).map(([role, count]) => (
            <span key={role} style={{ padding: '2px 8px', backgroundColor: 'rgba(6,182,212,0.15)', border: '1px solid #1e293b', borderRadius: '4px', fontSize: '10px', color: '#67e8f9', textTransform: 'capitalize' }}>
              {role}: {count}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
