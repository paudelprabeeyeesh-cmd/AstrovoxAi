import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { createTimeline, listTimelines, forkUniverse, getVisualization, mergeUniverses, collapseUniverse, exportTimeline, importTimeline } from '../../services/multiverseService'

const STATUS_COLORS = {
  active: '#34d399',
  forked: '#fbbf24',
  merged: '#a78bfa',
  collapsed: '#ef4444',
  paused: '#94a3b8',
}

export default function MultiverseDashboard({ onSelectTimeline, onSelectUniverse }) {
  const [timelines, setTimelines] = useState([])
  const [selectedTimeline, setSelectedTimeline] = useState(null)
  const [viz, setViz] = useState(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [branchType, setBranchType] = useState('conversation')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [forkName, setForkName] = useState('')
  const [modelOverride, setModelOverride] = useState('')
  const [mergeSource, setMergeSource] = useState('')
  const [mergeTarget, setMergeTarget] = useState('')
  const [mergeStrategy, setMergeStrategy] = useState('prefer_target')
  const [collapseId, setCollapseId] = useState('')
  const [importPayload, setImportPayload] = useState('')
  const [actionMessage, setActionMessage] = useState(null)

  useEffect(() => {
    loadTimelines()
  }, [])

  async function loadTimelines() {
    setLoading(true)
    setError(null)
    try {
      const data = await listTimelines()
      setTimelines(data.timelines || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleCreateTimeline(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const data = await createTimeline(name, description, branchType)
      setName('')
      setDescription('')
      await loadTimelines()
      const timeline = data.timeline
      setSelectedTimeline(timeline)
      onSelectTimeline?.(timeline)
      await loadVisualization(timeline.id)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleSelectTimeline(timeline) {
    setSelectedTimeline(timeline)
    onSelectTimeline?.(timeline)
    await loadVisualization(timeline.id)
  }

  async function loadVisualization(timelineId) {
    try {
      const data = await getVisualization(timelineId)
      setViz(data.visualization)
    } catch {
      setViz(null)
    }
  }

  async function handleFork(e) {
    e.preventDefault()
    if (!selectedTimeline || !forkName.trim()) return
    setLoading(true)
    setError(null)
    try {
      const data = await forkUniverse(selectedTimeline.id, forkName, null, modelOverride || undefined, undefined, undefined)
      setForkName('')
      setModelOverride('')
      onSelectUniverse?.(data.universe.id)
      await loadVisualization(selectedTimeline.id)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleMerge(e) {
    e.preventDefault()
    if (!mergeSource.trim() || !mergeTarget.trim()) return
    setLoading(true)
    setError(null)
    setActionMessage(null)
    try {
      const data = await mergeUniverses(mergeSource.trim(), mergeTarget.trim(), mergeStrategy)
      setActionMessage(`Merged: ${data.diff.summary}`)
      setMergeSource('')
      setMergeTarget('')
      if (selectedTimeline) await loadVisualization(selectedTimeline.id)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleCollapse(e) {
    e.preventDefault()
    if (!collapseId.trim()) return
    setLoading(true)
    setError(null)
    setActionMessage(null)
    try {
      await collapseUniverse(collapseId.trim())
      setActionMessage(`Universe ${collapseId.trim().slice(0, 8)}... collapsed`)
      setCollapseId('')
      if (selectedTimeline) await loadVisualization(selectedTimeline.id)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleExport() {
    if (!selectedTimeline) return
    setLoading(true)
    setError(null)
    setActionMessage(null)
    try {
      const data = await exportTimeline(selectedTimeline.id)
      const blob = new Blob([JSON.stringify(data.export, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `timeline-${selectedTimeline.id}.json`
      a.click()
      URL.revokeObjectURL(url)
      setActionMessage('Timeline exported')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleImport(e) {
    e.preventDefault()
    if (!importPayload.trim()) return
    setLoading(true)
    setError(null)
    setActionMessage(null)
    try {
      const payload = JSON.parse(importPayload)
      const data = await importTimeline(payload)
      setActionMessage(`Imported timeline: ${data.timeline.name}`)
      setImportPayload('')
      await loadTimelines()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '700', color: '#67e8f9', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '20px' }}>🌀</span>
            MULTIVERSE DASHBOARD
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '11px', color: '#64748b' }}>
            Simulate alternate timelines, branch realities, and debug causal divergences
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <select value={branchType} onChange={(e) => setBranchType(e.target.value)} style={{ padding: '6px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#cbd5e1', fontSize: '12px', fontFamily: 'inherit' }}>
            <option value="conversation">Conversation</option>
            <option value="scenario">Scenario</option>
            <option value="parallel">Parallel</option>
            <option value="divergence">Divergence</option>
          </select>
        </div>
      </div>

      {error && (
        <div style={{ backgroundColor: 'rgba(239,68,68,0.1)', border: '1px solid #ef4444', borderRadius: '8px', padding: '12px', fontSize: '12px', color: '#f87171' }}>
          ⚠️ {error}
        </div>
      )}

      {actionMessage && (
        <div style={{ backgroundColor: 'rgba(52,211,153,0.1)', border: '1px solid #34d399', borderRadius: '8px', padding: '12px', fontSize: '12px', color: '#34d399' }}>
          ✅ {actionMessage}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '16px', flex: 1, minHeight: 0 }}>
        {/* Left Panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflow: 'auto' }}>
          <form onSubmit={handleCreateTimeline} style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '12px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Timeline name" required style={{ padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#67e8f9', fontSize: '12px', fontFamily: 'inherit' }} />
            <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description (optional)" style={{ padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#cbd5e1', fontSize: '12px', fontFamily: 'inherit' }} />
            <button type="submit" disabled={loading || !name.trim()} style={{ padding: '8px 16px', backgroundColor: '#06b6d4', color: '#02040a', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '700', fontSize: '12px', opacity: loading || !name.trim() ? 0.5 : 1 }}>
              CREATE TIMELINE
            </button>
          </form>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {timelines.map((t) => (
              <button key={t.id} onClick={() => handleSelectTimeline(t)} style={{ padding: '10px 12px', backgroundColor: selectedTimeline?.id === t.id ? 'rgba(6,182,212,0.15)' : 'rgba(4,8,20,0.5)', border: `1px solid ${selectedTimeline?.id === t.id ? '#06b6d4' : '#1e293b'}`, borderRadius: '8px', color: selectedTimeline?.id === t.id ? '#67e8f9' : '#cbd5e1', cursor: 'pointer', textAlign: 'left', fontSize: '12px', fontFamily: 'inherit', transition: 'all 0.2s' }}>
                <div style={{ fontWeight: '600' }}>{t.name}</div>
                <div style={{ fontSize: '10px', color: '#64748b', marginTop: '2px' }}>{t.description || 'No description'} · {t.universes?.length || 0} universes</div>
              </button>
            ))}
            {timelines.length === 0 && !loading && (
              <div style={{ fontSize: '11px', color: '#475569', padding: '8px', textAlign: 'center' }}>No timelines yet. Create one to begin.</div>
            )}
          </div>
        </div>

        {/* Right Panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflow: 'auto' }}>
          {selectedTimeline && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ padding: '12px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <h3 style={{ margin: '0 0 8px', fontSize: '14px', color: '#67e8f9' }}>{selectedTimeline.name}</h3>
                  <p style={{ margin: 0, fontSize: '11px', color: '#64748b' }}>{selectedTimeline.description}</p>
                </div>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <button onClick={handleExport} disabled={loading} style={{ padding: '4px 10px', backgroundColor: 'rgba(6,182,212,0.15)', border: '1px solid #06b6d4', borderRadius: '6px', color: '#06b6d4', cursor: 'pointer', fontSize: '10px', fontFamily: 'inherit' }}>Export</button>
                </div>
              </div>

              <form onSubmit={handleFork} style={{ display: 'flex', gap: '8px', alignItems: 'center', padding: '12px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
                <input value={forkName} onChange={(e) => setForkName(e.target.value)} placeholder="Fork name" required style={{ flex: 1, padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#67e8f9', fontSize: '12px', fontFamily: 'inherit' }} />
                <input value={modelOverride} onChange={(e) => setModelOverride(e.target.value)} placeholder="Model override" style={{ width: '160px', padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#cbd5e1', fontSize: '12px', fontFamily: 'inherit' }} />
                <button type="submit" disabled={loading || !forkName.trim()} style={{ padding: '8px 16px', backgroundColor: '#a78bfa', color: '#02040a', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '700', fontSize: '12px', opacity: loading || !forkName.trim() ? 0.5 : 1 }}>
                  FORK REALITY
                </button>
              </form>

              <form onSubmit={handleMerge} style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '12px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
                <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Merge Universes</div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input value={mergeSource} onChange={(e) => setMergeSource(e.target.value)} placeholder="Source universe ID" required style={{ flex: 1, padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#67e8f9', fontSize: '12px', fontFamily: 'inherit' }} />
                  <input value={mergeTarget} onChange={(e) => setMergeTarget(e.target.value)} placeholder="Target universe ID" required style={{ flex: 1, padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#67e8f9', fontSize: '12px', fontFamily: 'inherit' }} />
                </div>
                <select value={mergeStrategy} onChange={(e) => setMergeStrategy(e.target.value)} style={{ padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#cbd5e1', fontSize: '12px', fontFamily: 'inherit' }}>
                  <option value="prefer_target">Prefer Target</option>
                  <option value="prefer_source">Prefer Source</option>
                  <option value="interleave">Interleave</option>
                  <option value="diff_only">Diff Only</option>
                </select>
                <button type="submit" disabled={loading || !mergeSource.trim() || !mergeTarget.trim()} style={{ padding: '8px 16px', backgroundColor: '#a78bfa', color: '#02040a', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '700', fontSize: '12px', opacity: loading || !mergeSource.trim() || !mergeTarget.trim() ? 0.5 : 1 }}>
                  MERGE UNIVERSES
                </button>
              </form>

              <form onSubmit={handleCollapse} style={{ display: 'flex', gap: '8px', alignItems: 'center', padding: '12px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
                <input value={collapseId} onChange={(e) => setCollapseId(e.target.value)} placeholder="Universe ID to collapse" required style={{ flex: 1, padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#f87171', fontSize: '12px', fontFamily: 'inherit' }} />
                <button type="submit" disabled={loading || !collapseId.trim()} style={{ padding: '8px 16px', backgroundColor: '#ef4444', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '700', fontSize: '12px', opacity: loading || !collapseId.trim() ? 0.5 : 1 }}>
                  COLLAPSE
                </button>
              </form>

              <details style={{ padding: '12px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
                <summary style={{ cursor: 'pointer', fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Import Timeline</summary>
                <form onSubmit={handleImport} style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
                  <textarea value={importPayload} onChange={(e) => setImportPayload(e.target.value)} placeholder='Paste exported timeline JSON here...' rows="4" style={{ padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#cbd5e1', fontSize: '11px', fontFamily: 'inherit', resize: 'vertical' }} />
                  <button type="submit" disabled={loading || !importPayload.trim()} style={{ padding: '8px 16px', backgroundColor: '#06b6d4', color: '#02040a', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '700', fontSize: '12px', opacity: loading || !importPayload.trim() ? 0.5 : 1 }}>
                    IMPORT TIMELINE
                  </button>
                </form>
              </details>

              {viz && (
                <div style={{ padding: '12px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
                  <h4 style={{ margin: '0 0 10px', fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Reality Graph</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {viz.nodes.map((node) => (
                      <button key={node.id} onClick={() => onSelectUniverse?.(node.id)} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 10px', backgroundColor: 'rgba(30,41,59,0.5)', borderRadius: '6px', fontSize: '11px', border: '1px solid #1e293b', cursor: 'pointer', color: '#cbd5e1', fontFamily: 'inherit', textAlign: 'left' }}>
                        <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: STATUS_COLORS[node.status] || '#64748b' }} />
                        <span style={{ color: '#cbd5e1', fontWeight: '500' }}>{node.label}</span>
                        <span style={{ marginLeft: 'auto', color: '#475569', fontSize: '10px' }}>gen {node.generation} · {node.message_count} msgs</span>
                      </button>
                    ))}
                  </div>
                  {viz.edges.length > 0 && (
                    <div style={{ marginTop: '8px', fontSize: '10px', color: '#475569' }}>
                      {viz.edges.map((edge, i) => (
                        <div key={i}>🔗 {edge.from.slice(0, 8)}... → {edge.to.slice(0, 8)}... ({edge.type})</div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '8px' }}>
                {[
                  { label: 'Universes', value: selectedTimeline.universes?.length || 0, color: '#67e8f9' },
                  { label: 'Branch Type', value: selectedTimeline.branch_type, color: '#a78bfa' },
                  { label: 'Status', value: 'active', color: '#34d399' },
                ].map((stat) => (
                  <div key={stat.label} style={{ padding: '10px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
                    <div style={{ fontSize: '10px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{stat.label}</div>
                    <div style={{ fontSize: '16px', fontWeight: '700', color: stat.color, marginTop: '4px' }}>{stat.value}</div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
          {!selectedTimeline && !loading && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '200px', color: '#475569', fontSize: '13px', textAlign: 'center' }}>
              Select or create a timeline to visualize reality branches
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
