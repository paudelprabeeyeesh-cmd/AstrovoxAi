import { useState } from 'react'
import { motion } from 'framer-motion'
import { warpSearchResults } from '../../services/realityWarpingService'

export default function RealityWarpingSearch({ results = [], onWarpedResults }) {
  const [perceptionMode, setPerceptionMode] = useState('standard')
  const [warped, setWarped] = useState([])

  const handleWarp = async () => {
    try {
      const data = await warpSearchResults('query', results, perceptionMode)
      setWarped(data.warped_results || [])
      onWarpedResults?.(data.warped_results)
    } catch (e) {
      console.error('Reality warping failed:', e)
    }
  }

  if (results.length === 0) return null

  return (
    <div style={{
      backgroundColor: 'rgba(4,8,20,0.6)',
      border: '1px solid #1e293b',
      borderRadius: '12px',
      padding: '16px'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h3 style={{
          margin: 0,
          fontSize: '13px',
          color: '#f59e0b',
          textTransform: 'uppercase',
          letterSpacing: '1px'
        }}>
          🌌 Reality-Warping Search
        </h3>
        <select
          value={perceptionMode}
          onChange={(e) => setPerceptionMode(e.target.value)}
          style={{
            background: 'var(--astrovox-surface)',
            border: '1px solid var(--astrovox-border)',
            color: 'var(--astrovox-text)',
            borderRadius: '4px',
            padding: '4px 8px',
            fontSize: '11px',
            cursor: 'pointer'
          }}
        >
          <option value="standard">Standard</option>
          <option value="quantum">Quantum</option>
          <option value="holographic">Holographic</option>
          <option value="transcendent">Transcendent</option>
          <option value="omniscient">Omniscient</option>
          <option value="omnipotent">Omnipotent</option>
          <option value="omnipresent">Omnipresent</option>
          <option value="infinite">Infinite</option>
        </select>
      </div>

      <button
        onClick={handleWarp}
        style={{
          width: '100%',
          padding: '8px',
          background: 'linear-gradient(135deg, #f59e0b, #ef4444)',
          border: 'none',
          borderRadius: '6px',
          color: '#02040a',
          fontSize: '12px',
          fontWeight: 700,
          cursor: 'pointer',
          marginBottom: '12px'
        }}
      >
        Warp Reality
      </button>

      {warped.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}
        >
          {warped.slice(0, 5).map((w, idx) => (
            <div key={w.result_id} style={{
              padding: '10px',
              backgroundColor: 'rgba(245,158,11,0.05)',
              border: '1px solid rgba(245,158,11,0.2)',
              borderRadius: '6px'
            }}>
              <div style={{ fontSize: '12px', color: '#e2e8f0', marginBottom: '4px' }}>
                {w.warped_content}
              </div>
              <div style={{ fontSize: '10px', color: '#64748b' }}>
                Warp factor: {(w.warp_factor * 100).toFixed(0)}% · Mode: {perceptionMode}
              </div>
            </div>
          ))}
        </motion.div>
      )}
    </div>
  )
}
