import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { runScenario } from '../../services/multiverseService'

export default function ScenarioEngine({ universeId, onResult }) {
  const [scenarioId, setScenarioId] = useState('')
  const [variables, setVariables] = useState('')
  const [iterations, setIterations] = useState(1)
  const [compareAgainst, setCompareAgainst] = useState('')
  const [running, setRunning] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)

  async function handleRun(e) {
    e.preventDefault()
    if (!universeId || running) return
    setRunning(true)
    setError(null)
    try {
      const vars = {}
      variables.split(',').filter(Boolean).forEach((pair) => {
        const [k, v] = pair.split('=')
        if (k && v) vars[k.trim()] = v.trim()
      })
      const data = await runScenario(universeId, scenarioId || 'default', vars, iterations, compareAgainst || undefined)
      setResults(data.results)
      onResult?.(data.results)
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '12px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
      <h4 style={{ margin: 0, fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>What-If Scenario Engine</h4>

      {error && <div style={{ fontSize: '11px', color: '#f87171' }}>⚠️ {error}</div>}

      <form onSubmit={handleRun} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <input value={scenarioId} onChange={(e) => setScenarioId(e.target.value)} placeholder="Scenario ID" style={{ padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#67e8f9', fontSize: '12px', fontFamily: 'inherit' }} />
        <input value={variables} onChange={(e) => setVariables(e.target.value)} placeholder="Variables (key=value, comma separated)" style={{ padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#cbd5e1', fontSize: '12px', fontFamily: 'inherit' }} />
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <input type="number" value={iterations} onChange={(e) => setIterations(parseInt(e.target.value) || 1)} min="1" max="100" placeholder="Iterations" style={{ width: '100px', padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#67e8f9', fontSize: '12px', fontFamily: 'inherit' }} />
          <input value={compareAgainst} onChange={(e) => setCompareAgainst(e.target.value)} placeholder="Compare against universe ID" style={{ flex: 1, padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#94a3b8', fontSize: '12px', fontFamily: 'inherit' }} />
        </div>
        <button type="submit" disabled={running || !universeId} style={{ padding: '8px 16px', backgroundColor: '#fbbf24', color: '#02040a', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '700', fontSize: '12px', opacity: running || !universeId ? 0.5 : 1 }}>
          {running ? 'Running Scenario...' : 'RUN SCENARIO'}
        </button>
      </form>

      {results && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {results.map((r, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} style={{ padding: '10px', backgroundColor: 'rgba(30,41,59,0.5)', border: '1px solid #1e293b', borderRadius: '6px', fontSize: '11px', color: '#cbd5e1' }}>
              <div style={{ fontWeight: '600', color: '#e2e8f0', marginBottom: '4px' }}>Iteration {r.iteration} · {r.latency_ms}ms · {r.tokens_used} tokens</div>
              <div style={{ color: '#94a3b8', lineHeight: '1.4' }}>{r.result?.final_content || '(no result)'}</div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
