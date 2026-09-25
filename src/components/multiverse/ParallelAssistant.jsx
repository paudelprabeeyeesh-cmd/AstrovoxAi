import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { runParallel } from '../../services/multiverseService'

const MODEL_SUGGESTIONS = ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'claude-3-5-sonnet', 'gemini-1.5-pro']

export default function ParallelAssistant({ universeId }) {
  const [variants, setVariants] = useState([
    { model: 'gpt-4o', temperature: 0.7, label: 'Primary', system_prompt_override: '' },
    { model: 'gpt-4o-mini', temperature: 0.9, label: 'Creative', system_prompt_override: '' },
  ])
  const [results, setResults] = useState(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState(null)

  function addVariant() {
    setVariants((prev) => [...prev, { model: 'gpt-4o', temperature: 0.7, label: `Variant ${prev.length + 1}`, system_prompt_override: '' }])
  }

  function updateVariant(index, field, value) {
    setVariants((prev) => prev.map((v, i) => i === index ? { ...v, [field]: value } : v))
  }

  function removeVariant(index) {
    setVariants((prev) => prev.filter((_, i) => i !== index))
  }

  async function handleRun() {
    if (!universeId || running) return
    setRunning(true)
    setError(null)
    try {
      const clean = variants.map(({ system_prompt_override, ...rest }) => ({
        ...rest,
        ...(system_prompt_override ? { system_prompt_override } : {}),
      }))
      const data = await runParallel(universeId, clean)
      setResults(data.run)
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '12px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h4 style={{ margin: 0, fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Parallel Assistant Variants</h4>
        <button onClick={addVariant} style={{ padding: '4px 10px', backgroundColor: 'rgba(167,139,250,0.15)', border: '1px solid #a78bfa', borderRadius: '6px', color: '#a78bfa', cursor: 'pointer', fontSize: '10px', fontFamily: 'inherit' }}>
          + Add Variant
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <AnimatePresence>
          {variants.map((variant, idx) => (
            <motion.div key={idx} initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} style={{ display: 'grid', gridTemplateColumns: '1fr 100px 80px 120px auto', gap: '8px', alignItems: 'center' }}>
              <input value={variant.label} onChange={(e) => updateVariant(idx, 'label', e.target.value)} placeholder="Label" style={{ padding: '6px 10px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#cbd5e1', fontSize: '11px', fontFamily: 'inherit' }} />
              <select value={variant.model} onChange={(e) => updateVariant(idx, 'model', e.target.value)} style={{ padding: '6px 10px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#cbd5e1', fontSize: '11px', fontFamily: 'inherit' }}>
                {MODEL_SUGGESTIONS.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
              <input type="number" value={variant.temperature} onChange={(e) => updateVariant(idx, 'temperature', parseFloat(e.target.value))} min="0" max="2" step="0.1" style={{ padding: '6px 10px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#67e8f9', fontSize: '11px', fontFamily: 'inherit', width: '60px' }} />
              <input value={variant.system_prompt_override} onChange={(e) => updateVariant(idx, 'system_prompt_override', e.target.value)} placeholder="System prompt (optional)" style={{ padding: '6px 10px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#94a3b8', fontSize: '11px', fontFamily: 'inherit' }} />
              <button type="button" onClick={() => removeVariant(idx)} style={{ padding: '4px 8px', backgroundColor: 'rgba(239,68,68,0.15)', border: '1px solid #ef4444', borderRadius: '6px', color: '#f87171', cursor: 'pointer', fontSize: '10px', fontFamily: 'inherit' }}>×</button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {error && <div style={{ fontSize: '11px', color: '#f87171' }}>⚠️ {error}</div>}

      <button onClick={handleRun} disabled={running || !universeId} style={{ padding: '8px 16px', backgroundColor: '#a78bfa', color: '#02040a', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '700', fontSize: '12px', opacity: running || !universeId ? 0.5 : 1 }}>
        {running ? 'Running Parallel Variants...' : 'RUN PARALLEL VARIANTS'}
      </button>

      {results && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Results</div>
          {results.results.map((r, i) => (
            <div key={i} style={{ padding: '8px 10px', backgroundColor: 'rgba(30,41,59,0.5)', border: '1px solid #1e293b', borderRadius: '6px', fontSize: '11px', color: '#cbd5e1' }}>
              <div style={{ fontWeight: '600', color: '#e2e8f0', marginBottom: '4px' }}>{r.label || r.model} · {r.temperature} · {r.latency_ms}ms</div>
              <div style={{ color: '#94a3b8', lineHeight: '1.4' }}>{r.result || '(empty)'}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
