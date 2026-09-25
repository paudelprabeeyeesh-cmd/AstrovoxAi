import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { getVisualization } from '../../services/multiverseService'

const STATUS_COLORS = {
  active: '#34d399',
  forked: '#fbbf24',
  merged: '#a78bfa',
  collapsed: '#ef4444',
  paused: '#94a3b8',
}

export default function ForkVisualizer({ timelineId, onSelectUniverse }) {
  const [viz, setViz] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!timelineId) return
    setLoading(true)
    getVisualization(timelineId)
      .then((data) => setViz(data.visualization))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [timelineId])

  if (loading) return <div style={{ color: '#64748b', fontSize: '12px', padding: '12px' }}>Loading reality graph...</div>
  if (error) return <div style={{ color: '#f87171', fontSize: '12px', padding: '12px' }}>⚠️ {error}</div>
  if (!viz) return <div style={{ color: '#475569', fontSize: '12px', padding: '12px' }}>Select a timeline to visualize forks</div>

  return (
    <div style={{ padding: '12px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
      <h4 style={{ margin: '0 0 12px', fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Reality Forks · {viz.timeline_name}</h4>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <AnimatePresence>
          {viz.nodes.map((node, idx) => (
            <motion.button
              key={node.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: idx * 0.05 }}
              onClick={() => onSelectUniverse?.(node.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '10px 12px',
                backgroundColor: 'rgba(30,41,59,0.5)',
                border: '1px solid #1e293b',
                borderRadius: '8px',
                cursor: 'pointer',
                textAlign: 'left',
                color: '#cbd5e1',
                fontFamily: 'inherit',
                fontSize: '12px',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#06b6d4'
                e.currentTarget.style.backgroundColor = 'rgba(6,182,212,0.08)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#1e293b'
                e.currentTarget.style.backgroundColor = 'rgba(30,41,59,0.5)'
              }}
            >
              <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: STATUS_COLORS[node.status] || '#64748b', boxShadow: `0 0 8px ${STATUS_COLORS[node.status] || '#64748b'}` }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: '600', color: '#e2e8f0' }}>{node.label}</div>
                <div style={{ fontSize: '10px', color: '#64748b', marginTop: '2px' }}>Generation {node.generation} · {node.message_count} messages</div>
              </div>
              <span style={{ fontSize: '10px', color: '#475569', padding: '2px 8px', border: '1px solid #1e293b', borderRadius: '4px', textTransform: 'capitalize' }}>{node.status}</span>
            </motion.button>
          ))}
        </AnimatePresence>
      </div>

      {viz.edges.length > 0 && (
        <div style={{ marginTop: '10px', padding: '8px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '6px', fontSize: '10px', color: '#475569' }}>
          {viz.edges.map((edge, i) => (
            <div key={i} style={{ marginBottom: '2px' }}>
              🔗 {edge.from.slice(0, 8)}... → {edge.to.slice(0, 8)}... <span style={{ color: '#64748b' }}>({edge.type})</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
