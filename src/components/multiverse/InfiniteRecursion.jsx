import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { recursiveBranch } from '../../services/multiverseService'

export default function InfiniteRecursion({ universeId }) {
  const [maxDepth, setMaxDepth] = useState(3)
  const [branchingFactor, setBranchingFactor] = useState(2)
  const [promptVariants, setPromptVariants] = useState('Alpha, Beta, Gamma, Delta, Echo')
  const [modelOverride, setModelOverride] = useState('')
  const [running, setRunning] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)

  async function handleRun(e) {
    e.preventDefault()
    if (!universeId || running) return
    setRunning(true)
    setError(null)
    setResults(null)
    try {
      const variants = promptVariants.split(',').map(v => v.trim()).filter(Boolean)
      const data = await recursiveBranch(universeId, maxDepth, branchingFactor, variants, modelOverride || undefined)
      setResults(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  const totalBranches = results ? Math.pow(branchingFactor, maxDepth) : 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '12px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
      <h4 style={{ margin: 0, fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Infinite Recursion Engine</h4>

      {error && <div style={{ fontSize: '11px', color: '#f87171' }}>⚠️ {error}</div>}

      <form onSubmit={handleRun} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <label style={{ fontSize: '11px', color: '#94a3b8', minWidth: '80px' }}>Max Depth</label>
          <input type="number" value={maxDepth} onChange={(e) => setMaxDepth(parseInt(e.target.value) || 1)} min="1" max="10" style={{ flex: 1, padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#67e8f9', fontSize: '12px', fontFamily: 'inherit' }} />
          <span style={{ fontSize: '10px', color: '#475569' }}>1-10</span>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <label style={{ fontSize: '11px', color: '#94a3b8', minWidth: '80px' }}>Branches</label>
          <input type="number" value={branchingFactor} onChange={(e) => setBranchingFactor(parseInt(e.target.value) || 1)} min="1" max="5" style={{ flex: 1, padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#67e8f9', fontSize: '12px', fontFamily: 'inherit' }} />
          <span style={{ fontSize: '10px', color: '#475569' }}>1-5</span>
        </div>

        <input value={promptVariants} onChange={(e) => setPromptVariants(e.target.value)} placeholder="Variants (comma separated)" style={{ padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#cbd5e1', fontSize: '12px', fontFamily: 'inherit' }} />
        <input value={modelOverride} onChange={(e) => setModelOverride(e.target.value)} placeholder="Model override (optional)" style={{ padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#94a3b8', fontSize: '12px', fontFamily: 'inherit' }} />

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '10px', color: '#475569' }}>
          <span>Safe termination: depth ≤ {maxDepth} · branches ≤ {branchingFactor}</span>
          <span>Total: {totalBranches} universes</span>
        </div>

        <button type="submit" disabled={running || !universeId} style={{ padding: '8px 16px', backgroundColor: '#fbbf24', color: '#02040a', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '700', fontSize: '12px', opacity: running || !universeId ? 0.5 : 1 }}>
          {running ? 'Branching Recursively...' : 'RUN RECURSIVE BRANCH'}
        </button>
      </form>

      {results && results.count > 0 && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '300px', overflowY: 'auto' }}>
          <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Created {results.count} universes
          </div>
          {results.universes.map((u, i) => (
            <div key={u.id} style={{ padding: '6px 10px', backgroundColor: 'rgba(30,41,59,0.5)', border: '1px solid #1e293b', borderRadius: '4px', fontSize: '11px', color: '#cbd5e1' }}>
              <span style={{ color: '#fbbf24', fontWeight: '600' }}>#{i + 1}</span>
              <span style={{ marginLeft: '8px' }}>{u.name}</span>
              <span style={{ marginLeft: 'auto', color: '#475569', fontSize: '10px' }}>gen {u.generation}</span>
            </div>
          ))}
        </motion.div>
      )}
    </div>
  )
}
