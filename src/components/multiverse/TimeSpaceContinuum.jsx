import { useState } from 'react'
import { motion } from 'framer-motion'
import { manipulateContinuum } from '../../services/multiverseService'

export default function TimeSpaceContinuum({ universeId }) {
  const [generationShift, setGenerationShift] = useState(0)
  const [temperatureOverride, setTemperatureOverride] = useState('')
  const [simulateTimeTravel, setSimulateTimeTravel] = useState(false)
  const [timeDelta, setTimeDelta] = useState('')
  const [collapseProbability, setCollapseProbability] = useState('')
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function handleManipulate(e) {
    e.preventDefault()
    setRunning(true)
    setError(null)
    setResult(null)
    try {
      const manipulation = {
        generation_shift: generationShift || undefined,
        temperature_override: temperatureOverride !== '' ? parseFloat(temperatureOverride) : undefined,
        simulate_time_travel: simulateTimeTravel,
        time_delta_seconds: timeDelta !== '' ? parseInt(timeDelta) : undefined,
        collapse_probability: collapseProbability !== '' ? parseFloat(collapseProbability) : undefined,
      }
      const data = await manipulateContinuum(universeId, manipulation)
      setResult(data.continuum)
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '12px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
      <h4 style={{ margin: 0, fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Time-Space Continuum</h4>

      {error && <div style={{ fontSize: '11px', color: '#f87171' }}>⚠️ {error}</div>}

      <form onSubmit={handleManipulate} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <label style={{ fontSize: '11px', color: '#94a3b8', minWidth: '100px' }}>Generation</label>
          <input type="number" value={generationShift} onChange={(e) => setGenerationShift(parseInt(e.target.value) || 0)} style={{ flex: 1, padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#67e8f9', fontSize: '12px', fontFamily: 'inherit' }} />
          <span style={{ fontSize: '10px', color: '#475569' }}>shift</span>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <label style={{ fontSize: '11px', color: '#94a3b8', minWidth: '100px' }}>Temperature</label>
          <input type="number" value={temperatureOverride} onChange={(e) => setTemperatureOverride(e.target.value)} step="0.1" min="0" max="2" placeholder="0.7" style={{ flex: 1, padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#67e8f9', fontSize: '12px', fontFamily: 'inherit' }} />
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <label style={{ fontSize: '11px', color: '#94a3b8', minWidth: '100px' }}>Time Delta</label>
          <input type="number" value={timeDelta} onChange={(e) => setTimeDelta(e.target.value)} placeholder="seconds" style={{ flex: 1, padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#67e8f9', fontSize: '12px', fontFamily: 'inherit' }} />
          <span style={{ fontSize: '10px', color: '#475569' }}>±86400</span>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <label style={{ fontSize: '11px', color: '#94a3b8', minWidth: '100px' }}>Collapse Risk</label>
          <input type="number" value={collapseProbability} onChange={(e) => setCollapseProbability(e.target.value)} step="0.01" min="0" max="1" placeholder="0.0 - 1.0" style={{ flex: 1, padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#67e8f9', fontSize: '12px', fontFamily: 'inherit' }} />
        </div>

        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: '#94a3b8', cursor: 'pointer' }}>
          <input type="checkbox" checked={simulateTimeTravel} onChange={(e) => setSimulateTimeTravel(e.target.checked)} style={{ accentColor: '#06b6d4' }} />
          Simulate time travel
        </label>

        <button type="submit" disabled={running || !universeId} style={{ padding: '8px 16px', backgroundColor: '#fbbf24', color: '#02040a', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '700', fontSize: '12px', opacity: running || !universeId ? 0.5 : 1 }}>
          {running ? 'Manipulating Continuum...' : 'MANIPULATE CONTINUUM'}
        </button>
      </form>

      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} style={{ padding: '10px', backgroundColor: 'rgba(30,41,59,0.5)', border: '1px solid #1e293b', borderRadius: '6px', fontSize: '11px', color: '#cbd5e1' }}>
          <div style={{ fontWeight: '600', color: '#e2e8f0', marginBottom: '4px' }}>Continuum Updated</div>
          <div>Generation: {result.generation} · Status: {result.status}</div>
          <div style={{ fontSize: '10px', color: '#64748b', marginTop: '4px' }}>{result.updated_at}</div>
        </motion.div>
      )}
    </div>
  )
}
