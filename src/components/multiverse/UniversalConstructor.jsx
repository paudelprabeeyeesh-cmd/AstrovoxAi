import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { runConstructor } from '../../services/multiverseService'

const BLUEPRINTS = [
  { name: 'Minimal Observer', description: 'Single-perspective minimal universe', parameters: {}, temperature: 0.3, branch_type: 'conversation' },
  { name: 'Creative Explosion', description: 'High-temperature divergent universe', parameters: { creativity_boost: true }, temperature: 1.5, branch_type: 'scenario' },
  { name: 'Debug Sandbox', description: 'Debugging-focused universe with verbose logging', parameters: { debug_mode: true, verbose: true }, temperature: 0.1, branch_type: 'divergence' },
  { name: 'Parallel Matrix', description: 'Multi-track parallel processing universe', parameters: { parallel_tracks: 4 }, temperature: 0.7, branch_type: 'parallel' },
  { name: 'Echo Chamber', description: 'Recursive self-reinforcing universe', parameters: { echo_factor: 0.9 }, temperature: 0.5, branch_type: 'conversation' },
]

export default function UniversalConstructor({ timelineId, onConstructed }) {
  const [selectedBlueprint, setSelectedBlueprint] = useState(null)
  const [customName, setCustomName] = useState('')
  const [customDescription, setCustomDescription] = useState('')
  const [customSystemPrompt, setCustomSystemPrompt] = useState('')
  const [customTemperature, setCustomTemperature] = useState(0.7)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function handleConstruct(e) {
    e.preventDefault()
    if (!timelineId || running) return
    setRunning(true)
    setError(null)
    setResult(null)
    try {
      const blueprint = selectedBlueprint || {
        name: customName || 'Custom Universe',
        description: customDescription || '',
        parameters: {},
        system_prompt_override: customSystemPrompt || '',
        temperature: customTemperature,
        branch_type: 'conversation',
      }
      const data = await runConstructor(timelineId, blueprint)
      setResult(data.universe)
      onConstructed?.(data.universe)
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '12px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
      <h4 style={{ margin: 0, fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Universal Constructor</h4>

      {error && <div style={{ fontSize: '11px', color: '#f87171' }}>⚠️ {error}</div>}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div style={{ fontSize: '10px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Blueprints</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '6px' }}>
          <AnimatePresence>
            {BLUEPRINTS.map((bp) => (
              <motion.button
                key={bp.name}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setSelectedBlueprint(bp)}
                style={{
                  padding: '10px',
                  backgroundColor: selectedBlueprint?.name === bp.name ? 'rgba(6,182,212,0.15)' : 'rgba(30,41,59,0.5)',
                  border: `1px solid ${selectedBlueprint?.name === bp.name ? '#06b6d4' : '#1e293b'}`,
                  borderRadius: '6px',
                  color: selectedBlueprint?.name === bp.name ? '#67e8f9' : '#cbd5e1',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '11px',
                  fontFamily: 'inherit',
                }}
              >
                <div style={{ fontWeight: '600', marginBottom: '2px' }}>{bp.name}</div>
                <div style={{ fontSize: '10px', color: '#64748b' }}>{bp.description}</div>
              </motion.button>
            ))}
          </AnimatePresence>
        </div>
      </div>

      <form onSubmit={handleConstruct} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <input value={customName} onChange={(e) => setCustomName(e.target.value)} placeholder="Custom universe name" style={{ padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#67e8f9', fontSize: '12px', fontFamily: 'inherit' }} />
        <textarea value={customDescription} onChange={(e) => setCustomDescription(e.target.value)} placeholder="Description" rows="2" style={{ padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#cbd5e1', fontSize: '12px', fontFamily: 'inherit', resize: 'vertical' }} />
        <input value={customSystemPrompt} onChange={(e) => setCustomSystemPrompt(e.target.value)} placeholder="System prompt override" style={{ padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#94a3b8', fontSize: '12px', fontFamily: 'inherit' }} />
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <label style={{ fontSize: '11px', color: '#94a3b8', minWidth: '80px' }}>Temperature</label>
          <input type="number" value={customTemperature} onChange={(e) => setCustomTemperature(parseFloat(e.target.value) || 0.7)} step="0.1" min="0" max="2" style={{ flex: 1, padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#67e8f9', fontSize: '12px', fontFamily: 'inherit' }} />
        </div>
        <button type="submit" disabled={running || !timelineId} style={{ padding: '8px 16px', backgroundColor: '#a78bfa', color: '#02040a', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '700', fontSize: '12px', opacity: running || !timelineId ? 0.5 : 1 }}>
          {running ? 'Constructing...' : 'CONSTRUCT UNIVERSE'}
        </button>
      </form>

      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} style={{ padding: '10px', backgroundColor: 'rgba(30,41,59,0.5)', border: '1px solid #1e293b', borderRadius: '6px', fontSize: '11px', color: '#cbd5e1' }}>
          <div style={{ fontWeight: '600', color: '#e2e8f0', marginBottom: '4px' }}>Constructed: {result.name}</div>
          <div style={{ fontSize: '10px', color: '#64748b' }}>{result.id} · {result.status}</div>
        </motion.div>
      )}
    </div>
  )
}
