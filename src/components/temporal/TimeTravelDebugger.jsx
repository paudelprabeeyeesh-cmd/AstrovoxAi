import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function TimeTravelDebugger() {
  const [aggregateId, setAggregateId] = useState('')
  const [timeSlices, setTimeSlices] = useState([])
  const [currentVersion, setCurrentVersion] = useState(0)
  const [direction, setDirection] = useState('forward')
  const [isPlaying, setIsPlaying] = useState(false)
  const [playbackSpeed, setPlaybackSpeed] = useState(1)
  const [selectedSlice, setSelectedSlice] = useState(null)
  const [currentState, setCurrentState] = useState({})
  const [eventLog, setEventLog] = useState([])
  const [snapshots, setSnapshots] = useState([])
  const [diffResult, setDiffResult] = useState(null)
  const [activeTab, setActiveTab] = useState('debugger')
  const [causalEvents, setCausalEvents] = useState([])
  const [branches, setBranches] = useState([])

  const timeTravel = useCallback((version) => {
    setCurrentVersion(version)
    const slice = timeSlices.find(s => s.version === version)
    setSelectedSlice(slice || null)
    if (slice) {
      setCurrentState(slice.state || {})
    }
  }, [timeSlices])

  const stepForward = useCallback(() => {
    timeTravel(currentVersion + 1)
  }, [currentVersion, timeTravel])

  const stepReverse = useCallback(() => {
    timeTravel(Math.max(0, currentVersion - 1))
  }, [currentVersion, timeTravel])

  const jumpToVersion = useCallback((version) => {
    timeTravel(version)
  }, [timeTravel])

  const jumpToSnapshot = useCallback((snapshotId) => {
    const snapshot = snapshots.find(s => s.snapshot_id === snapshotId)
    if (snapshot) {
      setCurrentVersion(snapshot.version)
      setCurrentState(snapshot.state || {})
      setSelectedSlice({ ...snapshot, event: {} })
    }
  }, [snapshots])

  const createBranch = useCallback((name) => {
    const branch = {
      branch_id: `branch_${Date.now()}`,
      name,
      type: 'experiment',
      status: 'active',
      created_at: new Date().toISOString(),
    }
    setBranches([...branches, branch])
  }, [branches])

  const rollbackToVersion = useCallback((version) => {
    setCurrentVersion(version)
    const targetSlice = timeSlices.find(s => s.version === version)
    if (targetSlice) {
      setCurrentState(targetSlice.state || {})
      setSelectedSlice(targetSlice)
    }
  }, [timeSlices])

  useEffect(() => {
    if (isPlaying) {
      const interval = setInterval(() => {
        setCurrentVersion(prev => {
          const next = direction === 'forward' ? prev + 1 : Math.max(0, prev - 1)
          return next
        })
      }, 1000 / playbackSpeed)
      return () => clearInterval(interval)
    }
  }, [isPlaying, direction, playbackSpeed])

  const formatState = (state) => {
    if (!state || Object.keys(state).length === 0) return 'Empty state'
    return Object.entries(state).map(([key, value]) => `${key}: ${JSON.stringify(value, null, 2)}`).join('\n')
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
        <input
          value={aggregateId}
          onChange={e => setAggregateId(e.target.value)}
          placeholder="Aggregate ID"
          style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '4px 8px', color: 'var(--astrovox-text)', fontSize: '11px', flex: 1 }}
        />
        <div style={{ display: 'flex', gap: '4px' }}>
          <button onClick={stepReverse} title="Step Back" style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', color: 'var(--astrovox-text)', padding: '2px 6px', cursor: 'pointer' }}><Icon name="play" size={12} style={{ transform: 'rotate(180deg)' }} /></button>
          <button onClick={() => setIsPlaying(!isPlaying)} title={isPlaying ? 'Pause' : 'Play'} style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', color: 'var(--astrovox-text)', padding: '4px 6px', cursor: 'pointer' }}><Icon name={isPlaying ? 'pause' : 'play'} size={12} /></button>
          <button onClick={stepForward} title="Step Forward" style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', color: 'var(--astrovox-text)', padding: '2px 6px', cursor: 'pointer' }}><Icon name="play" size={12} /></button>
        </div>
        <select value={direction} onChange={e => setDirection(e.target.value)} style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', color: 'var(--astrovox-text)', fontSize: '11px', padding: '2px 4px' }}>
          <option value="forward">Forward</option>
          <option value="reverse">Reverse</option>
        </select>
        <select value={playbackSpeed} onChange={e => setPlaybackSpeed(Number(e.target.value))} style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', color: 'var(--astrovox-text)', fontSize: '11px', padding: '2px 4px' }}>
          <option value="0.5">0.5x</option>
          <option value="1">1x</option>
          <option value="2">2x</option>
          <option value="4">4x</option>
        </select>
      </div>

      <div style={{ display: 'flex', gap: '8px', flex: 1, overflow: 'hidden' }}>
        <div style={{ width: '280px', display: 'flex', flexDirection: 'column', gap: '8px', overflow: 'auto' }}>
          <div style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px' }}>
            <h3 style={{ margin: '0 0 8px', fontSize: '11px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>Timeline</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', maxHeight: '200px', overflow: 'auto' }}>
              <AnimatePresence>
                {timeSlices.slice(0, 20).map(slice => (
                  <motion.div key={slice.version} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} onClick={() => jumpToVersion(slice.version)} style={{ padding: '4px 8px', borderRadius: 'var(--astrovox-radius)', cursor: 'pointer', fontSize: '10px', fontFamily: 'monospace', background: currentVersion === slice.version ? 'var(--astrovox-surface-hover)' : 'transparent', color: 'var(--astrovox-text)', border: '1px solid', borderColor: currentVersion === slice.version ? 'var(--astrovox-primary)' : 'transparent' }}>
                    v{slice.version} - {slice.event?.event_type || 'unknown'}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>

          <div style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px' }}>
            <h3 style={{ margin: '0 0 8px', fontSize: '11px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>Snapshots</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', maxHeight: '120px', overflow: 'auto' }}>
              {snapshots.map(snapshot => (
                <div key={snapshot.snapshot_id} onClick={() => jumpToSnapshot(snapshot.snapshot_id)} style={{ padding: '4px 8px', borderRadius: 'var(--astrovox-radius)', cursor: 'pointer', fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)', background: currentVersion === snapshot.version ? 'var(--astrovox-surface-hover)' : 'transparent' }}>
                  v{snapshot.version} - {new Date(snapshot.created_at).toLocaleTimeString()}
                </div>
              ))}
            </div>
          </div>

          <div style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px' }}>
            <h3 style={{ margin: '0 0 8px', fontSize: '11px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>Branches</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {branches.map(branch => (
                <div key={branch.branch_id} style={{ padding: '4px 8px', borderRadius: 'var(--astrovox-radius)', fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)', background: branch.status === 'active' ? 'var(--astrovox-surface-hover)' : 'transparent' }}>
                  {branch.name} ({branch.status})
                </div>
              ))}
            </div>
          </div>
        </div>

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px', overflow: 'auto' }}>
          <div style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px' }}>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
              {['debugger', 'state', 'diff', 'causal', 'branches'].map(tab => (
                <button key={tab} onClick={() => setActiveTab(tab)} style={{ background: activeTab === tab ? 'var(--astrovox-surface-hover)' : 'transparent', border: '1px solid', borderColor: activeTab === tab ? 'var(--astrovox-primary)' : 'transparent', borderRadius: 'var(--astrovox-radius)', color: 'var(--astrovox-text)', padding: '4px 8px', cursor: 'pointer', fontSize: '10px', textTransform: 'uppercase' }}>
                  {tab}
                </button>
              ))}
            </div>
            <AnimatePresence mode="wait">
              {activeTab === 'debugger' && (
                <motion.div key="debugger" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <span style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', fontFamily: 'monospace' }}>Version: {currentVersion}</span>
                    <span style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', fontFamily: 'monospace' }}>Direction: {direction}</span>
                    <span style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', fontFamily: 'monospace' }}>State: {JSON.stringify(currentState).slice(0, 50)}...</span>
                  </div>
                  <pre style={{ background: 'var(--astrovox-bg)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px', fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)', overflow: 'auto', maxHeight: '300px', whiteSpace: 'pre-wrap' }}>
                    {formatState(currentState)}
                  </pre>
                </motion.div>
              )}
              {activeTab === 'state' && (
                <motion.div key="state" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <pre style={{ background: 'var(--astrovox-bg)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px', fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)', overflow: 'auto', maxHeight: '300px', whiteSpace: 'pre-wrap' }}>
                    {JSON.stringify(currentState, null, 2)}
                  </pre>
                </motion.div>
              )}
              {activeTab === 'diff' && (
                <motion.div key="diff" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <pre style={{ background: 'var(--astrovox-bg)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px', fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)', overflow: 'auto', maxHeight: '300px', whiteSpace: 'pre-wrap' }}>
                    {diffResult ? JSON.stringify(diffResult, null, 2) : 'No diff computed'}
                  </pre>
                </motion.div>
              )}
              {activeTab === 'causal' && (
                <motion.div key="causal" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {causalEvents.slice(0, 10).map(event => (
                      <div key={event.event_id} style={{ padding: '4px 8px', borderRadius: 'var(--astrovox-radius)', fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)', background: 'var(--astrovox-surface)' }}>
                        {event.event_type} - {event.occurred_at}
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
              {activeTab === 'branches' && (
                <motion.div key="branches" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                    <input placeholder="Branch name" id="branch-name" style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '4px 8px', color: 'var(--astrovox-text)', fontSize: '11px', flex: 1 }} />
                    <button onClick={() => createBranch(document.getElementById('branch-name')?.value || 'branch')} style={{ background: 'var(--astrovox-primary)', border: 'none', borderRadius: 'var(--astrovox-radius)', color: 'var(--astrovox-text)', padding: '4px 8px', cursor: 'pointer', fontSize: '10px' }}>Create</button>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {branches.map(branch => (
                      <div key={branch.branch_id} style={{ padding: '4px 8px', borderRadius: 'var(--astrovox-radius)', fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)', background: 'var(--astrovox-surface)' }}>
                        {branch.name} - {branch.status}
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  )
}
