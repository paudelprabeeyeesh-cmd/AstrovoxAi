import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { portalNavigate, listTimelines } from '../../services/multiverseService'

export default function DimensionalPortal({ universeId }) {
  const [targetId, setTargetId] = useState('')
  const [mergeOnArrival, setMergeOnArrival] = useState(false)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [recentPortals, setRecentPortals] = useState([])

  useEffect(() => {
    const saved = localStorage.getItem('recent_portals')
    if (saved) {
      try { setRecentPortals(JSON.parse(saved)) } catch {}
    }
  }, [])

  async function handleNavigate(e) {
    e.preventDefault()
    if (!universeId || !targetId || running) return
    setRunning(true)
    setError(null)
    setResult(null)
    try {
      const data = await portalNavigate(universeId, targetId, mergeOnArrival)
      setResult(data.portal)
      const updated = [{ from: universeId, to: targetId, time: new Date().toISOString() }, ...recentPortals].slice(0, 10)
      setRecentPortals(updated)
      localStorage.setItem('recent_portals', JSON.stringify(updated))
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '12px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
      <h4 style={{ margin: 0, fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Dimensional Portal</h4>

      {error && <div style={{ fontSize: '11px', color: '#f87171' }}>⚠️ {error}</div>}

      <form onSubmit={handleNavigate} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{ fontSize: '10px', color: '#475569', minWidth: '60px' }}>FROM</span>
          <code style={{ flex: 1, padding: '6px 10px', backgroundColor: 'rgba(30,41,59,0.5)', border: '1px solid #1e293b', borderRadius: '4px', color: '#06b6d4', fontSize: '10px' }}>{universeId?.slice(0, 12) || 'none'}...</code>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{ fontSize: '10px', color: '#475569', minWidth: '60px' }}>TO</span>
          <input value={targetId} onChange={(e) => setTargetId(e.target.value)} placeholder="Target universe ID" required style={{ flex: 1, padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#67e8f9', fontSize: '12px', fontFamily: 'inherit' }} />
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: '#94a3b8', cursor: 'pointer' }}>
          <input type="checkbox" checked={mergeOnArrival} onChange={(e) => setMergeOnArrival(e.target.checked)} style={{ accentColor: '#06b6d4' }} />
          Merge on arrival (interleave)
        </label>
        <button type="submit" disabled={running || !universeId || !targetId} style={{ padding: '8px 16px', backgroundColor: '#a78bfa', color: '#02040a', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '700', fontSize: '12px', opacity: running || !universeId || !targetId ? 0.5 : 1 }}>
          {running ? 'Opening Portal...' : 'OPEN PORTAL'}
        </button>
      </form>

      {result && (
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} style={{ padding: '10px', backgroundColor: 'rgba(30,41,59,0.5)', border: '1px solid #a78bfa', borderRadius: '6px', fontSize: '11px', color: '#cbd5e1' }}>
          <div style={{ fontWeight: '600', color: '#e2e8f0', marginBottom: '4px' }}>Portal Opened</div>
          <div>Target: {result.target_name} · Status: {result.target_status} · Gen {result.target_generation}</div>
          <div style={{ fontSize: '10px', color: '#64748b', marginTop: '4px' }}>Arrived at {result.arrival_timestamp}</div>
        </motion.div>
      )}

      {recentPortals.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div style={{ fontSize: '10px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Recent Jumps</div>
          {recentPortals.map((p, i) => (
            <div key={i} style={{ padding: '4px 8px', backgroundColor: 'rgba(30,41,59,0.3)', borderRadius: '4px', fontSize: '10px', color: '#94a3b8' }}>
              {p.from?.slice(0, 8)}... → {p.to?.slice(0, 8)}... · {new Date(p.time).toLocaleTimeString()}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
