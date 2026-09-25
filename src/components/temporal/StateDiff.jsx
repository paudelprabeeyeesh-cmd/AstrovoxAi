import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from ' 'framer-motion'
import Icon from '../../design/Iconography'

export default function StateDiff({ states, onSelectState, currentState, versionA, versionB, onDiff }) {
  const [stateA, setStateA] = useState(null)
  const [stateB, setStateB] = useState(null)
  const [diffResult, setDiffResult] = useState(null)
  const [viewMode, setViewMode] = useState('split')
  const [selectedHunk, setSelectedHunk] = useState(null)
  const [similarity, setSimilarity] = useState(100)
  const [score, setScore] = useState(0)
  const [stats, setStats] = useState({ additions: 0, deletions: 0, modifications: 0, unchanged: 0 })

  useEffect(() => {
    if (states && states.length >= 2) {
      setStateA(states[0])
      setStateB(states[1])
    }
  }, [states])

  useEffect(() => {
    if (currentState && !stateA) {
      setStateA(currentState)
    }
  }, [currentState, stateA])

  const computeDiff = useCallback((stateA, stateB) => {
    if (!stateA || !stateB) return null
    const additions = []
    const deletions = []
    const modifications = []
    const unchanged = []
    const keys = new Set([...Object.keys(stateA), ...Object.keys(stateB)])
    for (const key of keys) {
      if (key in stateA && key in stateB) {
        if (stateA[key] === stateB[key]) {
          unchanged.push({ field: key, value: stateA[key] })
        } else {
          modifications.push({ field: key, value_a: stateA[key], value_b: stateB[key] })
        }
      } else if (key in stateB) {
        additions.push({ field: key, value: stateB[key] })
      } else {
        deletions.push({ field: key, value: stateA[key] })
      }
    }
    const total = additions.length + deletions.length + modifications.length + unchanged.length
    const similarity = total ? (unchanged.length / total) * 100 : 100.0
    return { additions, deletions, modifications, unchanged, score: modifications.length + additions.length + deletions.length, similarity }
  }, [])

  const handleDiff = useCallback((stateA, stateB) => {
    setStateA(stateA)
    setStateB(stateB)
    const result = computeDiff(stateA, stateB)
    setDiffResult(result)
    if (result) {
      setStats({ additions: result.additions.length, deletions: result.deletions.length, modifications: result.modifications.length, unchanged: result.unchanged.length })
      setSimilarity(result.similarity)
      setScore(result.score)
    }
    onDiff?.(result)
  }, [computeDiff, onDiff])

  useEffect(() => {
    if (stateA && stateB) {
      handleDiff(stateA, stateB)
    }
  }, [stateA, stateB, handleDiff])

  const formatState = (state) => {
    if (!state || Object.keys(state).length === 0) return 'Empty state'
    return JSON.stringify(state, null, 2)
  }

  const getChangeType = (field, additions, deletions, modifications) => {
    if (additions.some(a => a.field === field)) return 'add'
    if (deletions.some(d => d.field === field)) return 'del'
    if (modifications.some(m => m.field === field)) return 'mod'
    return 'same'
  }

  const getChangeColor = (type) => {
    if (type === 'add') return 'var(--astrovox-success)'
    if (type === 'del') return 'var(--astrovox-error)'
    if (type === 'mod') return 'var(--astrovox-warning)'
    return 'var(--astrovox-text-muted)'
  }

  const renderField = (field, value, additions, deletions, modifications, stateA, stateB) => {
    const type = getChangeType(field, additions, deletions, modifications)
    return (
      <div key={field} style={{ display: 'flex', gap: '8px', padding: '4px 8px', borderRadius: 'var(--astrovox-radius)', background: type === 'add' ? 'var(--astrovox-success)' : type === 'del' ? 'var(--astrovox-error)' : type === 'mod' ? 'var(--astrovox-warning)' : 'transparent', opacity: type === 'same' ? 0.5 : 1 }}>
        <span style={{ fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)', flex: 1 }}>{field}</span>
        <span style={{ fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)', opacity: 0.7, maxWidth: '50%', overflow: 'hidden', textOverflow: 'ellipsis' }}>{JSON.stringify(value)}</span>
        <span style={{ fontSize: '9px', color: 'var(--astrovox-text-muted)', fontFamily: 'monospace' }}>{type}</span>
      </div>
    )
  }

  const splitView = () => {
    if (!stateA || !stateB || !diffResult) return null
    return (
      <div style={{ display: 'flex', gap: '8px' }}>
        <div style={{ flex: 1, background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px', overflow: 'auto', maxHeight: '300px' }}>
          <h4 style={{ margin: '0 0 8px', fontSize: '11px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>State A</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {Object.entries(stateA).map(([field, value]) => renderField(field, value, diffResult.additions, diffResult.deletions, diffResult.modifications, stateA, stateB))}
          </div>
        </div>
        <div style={{ flex: 1, background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px', overflow: 'auto', maxHeight: '300px' }}>
          <h4 style={{ margin: '0 0 8px', fontSize: '11px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>State B</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {Object.entries(stateB).map(([field, value]) => renderField(field, value, diffResult.additions, diffResult.deletions, diffResult.modifications, stateA, stateB))}
          </div>
        </div>
      </div>
    )
  }

  const unifiedView = () => {
    if (!stateA || !stateB || !diffResult) return null
    const keys = new Set([...Object.keys(stateA), ...Object.keys(stateB)])
    return (
      <div style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px', overflow: 'auto', maxHeight: '300px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {Array.from(keys).map(field => {
            const type = getChangeType(field, diffResult.additions, diffResult.deletions, diffResult.modifications)
            return (
              <div key={field} style={{ display: 'flex', gap: '8px', padding: '4px 8px', borderRadius: 'var(--astrovox-radius)', background: type === 'add' ? 'var(--astrovox-success)' : type === 'del' ? 'var(--astrovox-error)' : type === 'mod' ? 'var(--astrovox-warning)' : 'transparent', opacity: type === 'same' ? 0.5 : 1 }}>
                <span style={{ fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)', flex: 1 }}>{field}</span>
                <span style={{ fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)', opacity: 0.7, maxWidth: '50%', overflow: 'hidden', textOverflow: 'ellipsis' }}>{JSON.stringify(type === 'add' ? stateB[field] : type === 'del' ? stateA[field] : stateA[field])}</span>
                <span style={{ fontSize: '9px', color: 'var(--astrovox-text-muted)', fontFamily: 'monospace' }}>{type}</span>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  const statsView = () => {
    if (!diffResult) return null
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          <div style={{ flex: 1, background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px', textAlign: 'center' }}>
            <span style={{ fontSize: '16px', fontFamily: 'monospace', color: 'var(--astrovox-success)' }}>{stats.additions}</span>
            <div style={{ fontSize: '9px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase' }}>Additions</div>
          </div>
          <div style={{ flex: 1, background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px', textAlign: 'center' }}>
            <span style={{ fontSize: '16px', fontFamily: 'monospace', color: 'var(--astrovox-error)' }}>{stats.deletions}</span>
            <div style={{ fontSize: '9px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase' }}>Deletions</div>
          </div>
          <div style={{ flex: 1, background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px', textAlign: 'center' }}>
            <span style={{ fontSize: '16px', fontFamily: 'monospace', color: 'var(--astrovox-warning)' }}>{stats.modifications}</span>
            <div style={{ fontSize: '9px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase' }}>Modifications</div>
          </div>
        </div>
        <div style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px', textAlign: 'center' }}>
          <span style={{ fontSize: '24px', fontFamily: 'monospace', color: 'var(--astrovox-text)' }}>{similarity.toFixed(1)}%</span>
          <div style={{ fontSize: '9px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase' }}>Similarity</div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', padding: '4px' }}>
        <select value={viewMode} onChange={e => setViewMode(e.target.value)} style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', color: 'var(--astrovox-text)', fontSize: '11px', padding: '2px 4px' }}>
          <option value="split">Split View</option>
          <option value="unified">Unified View</option>
          <option value="stats">Statistics</option>
        </select>
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px', overflow: 'auto' }}>
        {viewMode === 'split' && splitView()}
        {viewMode === 'unified' && unifiedView()}
        {viewMode === 'stats' && statsView()}
      </div>
    </div>
  )
}
