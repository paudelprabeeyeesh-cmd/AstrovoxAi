import { useState, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { getUniverseMessages } from '../../services/multiverseService'

export default function DivergenceTracker({ universeA, universeB }) {
  const [messagesA, setMessagesA] = useState([])
  const [messagesB, setMessagesB] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!universeA || !universeB) return
    setLoading(true)
    Promise.all([
      getUniverseMessages(universeA, 200, 0),
      getUniverseMessages(universeB, 200, 0),
    ]).then(([a, b]) => {
      setMessagesA(a.messages || [])
      setMessagesB(b.messages || [])
    }).catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [universeA, universeB])

  const diff = useMemo(() => {
    const max = Math.max(messagesA.length, messagesB.length)
    const points = []
    for (let i = 0; i < max; i++) {
      const a = messagesA[i]
      const b = messagesB[i]
      if (a && b && a.content !== b.content) {
        points.push({ index: i, type: 'content_drift', contentA: a.content, contentB: b.content, role: a.role })
      } else if (a && !b) {
        points.push({ index: i, type: 'added_in_a', contentA: a.content, role: a.role })
      } else if (!a && b) {
        points.push({ index: i, type: 'added_in_b', contentB: b.content, role: b.role })
      }
    }
    return points
  }, [messagesA, messagesB])

  if (!universeA || !universeB) {
    return <div style={{ color: '#475569', fontSize: '12px', padding: '12px', textAlign: 'center' }}>Select two universes to track causal divergence</div>
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '12px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h4 style={{ margin: 0, fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Causal Divergence Tracker</h4>
        <span style={{ fontSize: '10px', color: '#475569' }}>{diff.length} divergence points</span>
      </div>

      {error && <div style={{ fontSize: '11px', color: '#f87171' }}>⚠️ {error}</div>}

      {loading && <div style={{ color: '#64748b', fontSize: '12px' }}>Analyzing causal drift...</div>}

      <div style={{ display: 'flex', gap: '8px', fontSize: '10px', color: '#64748b' }}>
        <span>Universe A: <span style={{ color: '#06b6d4' }}>{universeA.slice(0, 8)}...</span></span>
        <span>Universe B: <span style={{ color: '#a78bfa' }}>{universeB.slice(0, 8)}...</span></span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '400px', overflowY: 'auto' }}>
        {diff.length === 0 && !loading && (
          <div style={{ color: '#34d399', fontSize: '11px', textAlign: 'center', padding: '12px' }}>No divergence detected — universes are aligned.</div>
        )}
        {diff.map((point, i) => (
          <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} style={{ padding: '8px 10px', backgroundColor: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.3)', borderRadius: '6px', fontSize: '11px', color: '#cbd5e1' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <span style={{ color: '#fbbf24', fontWeight: '600', fontSize: '10px', textTransform: 'uppercase' }}>Divergence #{point.index + 1}</span>
              <span style={{ fontSize: '9px', color: '#64748b', padding: '2px 6px', backgroundColor: 'rgba(30,41,59,0.5)', borderRadius: '4px', textTransform: 'capitalize' }}>{point.type.replace(/_/g, ' ')}</span>
            </div>
            {point.contentA && <div style={{ color: '#94a3b8', fontSize: '10px', marginBottom: '2px' }}>A: {point.contentA.slice(0, 100)}{point.contentA.length > 100 ? '...' : ''}</div>}
            {point.contentB && <div style={{ color: '#94a3b8', fontSize: '10px' }}>B: {point.contentB.slice(0, 100)}{point.contentB.length > 100 ? '...' : ''}</div>}
          </motion.div>
        ))}
      </div>
    </div>
  )
}
