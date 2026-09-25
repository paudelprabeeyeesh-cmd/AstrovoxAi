import { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from ' 'framer-motion'
import Icon from '../../design/Iconography'

export default function Timeline({ events, onTimeTravel, onSnapshot, onBranch }) {
  const [timeScale, setTimeScale] = useState('hours')
  const [filter, setFilter] = useState('all')
  const [selectedEvent, setSelectedEvent] = useState(null)
  const [tooltip, setTooltip] = useState(null)
  const canvasRef = useRef(null)
  const [eventsData, setEventsData] = useState(events || [])
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [currentTimeIndex, setCurrentTimeIndex] = useState(0)
  const [currentTime, setCurrentTime] = useState(new Date())
  const [branches, setBranches] = useState([])
  const [snapshots, setSnapshots] = useState([])
  const [showBranches, setShowBranches] = useState(true)
  const [showSnapshots, setShowSnapshots] = useState(true)
  const [showEvents, setShowEvents] = useState(true)
  const [zoomLevel, setZoomLevel] = useState(1)
  const [panOffset, setPanOffset] = useState(0)
  const [currentEventIndex, setCurrentEventIndex] = useState(0)
  const [currentState, setCurrentState] = useState({})
  const [history, setHistory] = useState([])
  const [preview, setPreview] = useState(null)

  const timeScaleOptions = {
    minutes: 60000,
    hours: 3600000,
    days: 86400000,
    weeks: 604800000,
    months: 2592000000,
  }

  const msPerPixel = timeScaleOptions[timeScale] / (200 * zoomLevel)

  const generateTimelineData = useCallback(() => {
    return eventsData.map((event, index) => ({
      ...event,
      id: event.id || `evt_${index}`,
      timestamp: event.timestamp || new Date(Date.now() - index * 60000).toISOString(),
      x: (Date.now() - new Date(event.timestamp || Date.now()).getTime()) / msPerPixel + panOffset,
      y: event.type === 'snapshot' ? 50 : event.type === 'branch' ? 100 : 0,
      style: event.type === 'snapshot' ? { width: 12, height: 12, borderRadius: '50%', background: 'var(--astrovox-primary)', border: '2px solid var(--astrovox-primary)', cursor: 'pointer' } : event.type === 'branch' ? { width: 12, height: 12, borderRadius: '4px', background: 'var(--astrovox-success)', border: '2px solid var(--astrovox-success)', cursor: 'pointer' } : { width: 8, height: 8, borderRadius: '50%', background: 'var(--astrovox-text-muted)', border: '1px solid var(--astrovox-text-muted)', cursor: 'pointer' },
      tooltip: event.tooltip || event.type,
    }))
  }, [eventsData, msPerPixel, panOffset])

  const timelineData = generateTimelineData()

  const timeTravelToEvent = useCallback((event) => {
    const eventData = timelineData.find(e => e.id === event.id)
    if (eventData) {
      setCurrentEventIndex(timelineData.indexOf(eventData))
    }
    setCurrentState(event.data || {})
    setCurrentTime(new Date(event.timestamp))
    setSelectedEvent(event)
    onTimeTravel?.(event)
  }, [timelineData, onTimeTravel])

  const play = useCallback(() => {
    setPlaying(true)
  }, [])

  const pause = useCallback(() => {
    setPlaying(false)
  }, [])

  const stepForward = useCallback(() => {
    const nextIndex = Math.min(currentEventIndex + 1, timelineData.length - 1)
    setCurrentEventIndex(nextIndex)
    const event = timelineData[nextIndex]
    if (event) {
      setCurrentState(event.data || {})
      setCurrentTime(new Date(event.timestamp))
      setSelectedEvent(event)
    }
  }, [currentEventIndex, timelineData])

  const stepReverse = useCallback(() => {
    const prevIndex = Math.max(currentEventIndex - 1, 0)
    setCurrentEventIndex(prevIndex)
    const event = timelineData[prevIndex]
    if (event) {
      setCurrentState(event.data || {})
      setCurrentTime(new Date(event.timestamp))
      setSelectedEvent(event)
    }
  }, [currentEventIndex, timelineData])

  const createBranch = useCallback((name) => {
    const branch = {
      branch_id: `branch_${Date.now()}`,
      name,
      type: 'experiment',
      status: 'active',
      created_at: new Date().toISOString(),
    }
    setBranches([...branches, branch])
    onBranch?.(branch)
  }, [branches, onBranch])

  const deleteBranch = useCallback((branchId) => {
    setBranches(branches.filter(b => b.branch_id !== branchId))
  }, [branches])

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', padding: '4px' }}>
        <select value={timeScale} onChange={e => setTimeScale(e.target.value)} style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', color: 'var(--astrovox-text)', fontSize: '11px', padding: '2px 4px' }}>
          <option value="minutes">Minutes</option>
          <option value="hours">Hours</option>
          <option value="days">Days</option>
          <option value="weeks">Weeks</option>
          <option value="months">Months</option>
        </select>
        <select value={filter} onChange={e => setFilter(e.target.value)} style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', color: 'var(--astrovox-text)', fontSize: '11px', padding: '2px 4px' }}>
          <option value="all">All</option>
          <option value="state">State</option>
          <option value="snapshot">Snapshots</option>
          <option value="branch">Branches</option>
        </select>
        <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: 'var(--astrovox-text-muted)', cursor: 'pointer' }}>
          <input type="checkbox" checked={showBranches} onChange={e => setShowBranches(e.target.checked)} /> Branches
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: 'var(--astrovox-text-muted)', cursor: 'pointer' }}>
          <input type="checkbox" checked={showSnapshots} onChange={e => setShowSnapshots(e.target.checked)} /> Snapshots
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: 'var(--astrovox-text-muted)', cursor: 'pointer' }}>
          <input type="checkbox" checked={showEvents} onChange={e => setShowEvents(e.target.checked)} /> Events
        </label>
        <input type="range" min="0.5" max="4" step="0.5" value={speed} onChange={e => setSpeed(Number(e.target.value))} style={{ flex: 1, maxWidth: '100px' }} />
        <span style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', fontFamily: 'monospace' }}>{speed}x</span>
        <button onClick={play} style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', color: 'var(--astrovox-text)', padding: '2px 6px', cursor: 'pointer' }}><Icon name="play" size={12} /></button>
        <button onClick={pause} style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', color: 'var(--astrovox-text)', padding: '2px 6px', cursor: 'pointer' }}><Icon name="pause" size={12} /></button>
        <button onClick={stepForward} style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', color: 'var(--astrovox-text)', padding: '2px 6px', cursor: 'pointer' }}><Icon name="play" size={12} /></button>
        <button onClick={stepReverse} style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', color: 'var(--astrovox-text)', padding: '2px 6px', cursor: 'pointer' }}><Icon name="play" size={12} style={{ transform: 'rotate(180deg)' }} /></button>
        <button onClick={() => setShowBranches(!showBranches)} style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', color: 'var(--astrovox-text)', padding: '2px 6px', cursor: 'pointer' }}><Icon name="git-branch" size={12} /></button>
      </div>

      <div style={{ flex: 1, display: 'flex', gap: '8px', overflow: 'hidden' }}>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px', overflow: 'hidden' }}>
          <div style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px', position: 'relative', minHeight: '300px', overflow: 'auto' }}>
            <div style={{ position: 'relative', height: '100%', minWidth: '500px' }}>
              <div style={{ position: 'absolute', top: '40px', bottom: '0', left: '0', right: '0', borderTop: '1px solid var(--astrovox-border)', borderBottom: '1px solid var(--astrovox-border)' }} />
              <div style={{ position: 'absolute', top: '40px', bottom: '0', left: '0', right: '0', background: 'linear-gradient(to bottom, transparent 0%, var(--astrovox-surface) 100%)', opacity: 0.05 }} />
              <div style={{ position: 'absolute', left: `${panOffset + 100}px`, top: '50%', width: '2px', height: '100%', background: 'var(--astrovox-primary)', opacity: 0.3 }} />
              {timelineData.map((eventData, index) => {
                if (filter === 'snapshot' && eventData.type !== 'snapshot') return null
                if (filter === 'branch' && eventData.type !== 'branch') return null
                if (filter === 'state' && (eventData.type === 'snapshot' || eventData.type === 'branch')) return null
                return (
                  <div key={eventData.id} style={{ position: 'absolute', left: `${eventData.x}px`, top: `${eventData.y}px`, ...eventData.style }} onMouseEnter={() => setTooltip(eventData.tooltip)} onMouseLeave={() => setTooltip(null)} onClick={() => timeTravelToEvent(eventData)} />
                )
              })}
              {tooltip && (
                <div style={{ position: 'absolute', background: 'var(--astrovox-bg)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '4px 8px', fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)', zIndex: 10, pointerEvents: 'none' }}>
                  {tooltip}
                </div>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px', overflow: 'auto' }}>
            {history.slice(0, 20).map((item, index) => (
              <div key={index} onClick={() => setCurrentEventIndex(index)} style={{ padding: '4px 8px', borderRadius: 'var(--astrovox-radius)', fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)', background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', cursor: 'pointer' }}>
                {formatTime(item.timestamp)} - {item.type}
              </div>
            ))}
          </div>
        </div>

        <div style={{ width: '300px', display: 'flex', flexDirection: 'column', gap: '8px', overflow: 'auto' }}>
          <div style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px' }}>
            <h3 style={{ margin: '0 0 8px', fontSize: '11px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>Current State</h3>
            <pre style={{ background: 'var(--astrovox-bg)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px', fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)', overflow: 'auto', maxHeight: '200px', whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(currentState, null, 2) || 'Empty state'}
            </pre>
          </div>
          <div style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px' }}>
            <h3 style={{ margin: '0 0 8px', fontSize: '11px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>Branches</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {branches.map(branch => (
                <div key={branch.branch_id} style={{ padding: '4px 8px', borderRadius: 'var(--astrovox-radius)', fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)', background: branch.status === 'active' ? 'var(--astrovox-surface-hover)' : 'transparent', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>{branch.name}</span>
                  <button onClick={() => deleteBranch(branch.branch_id)} style={{ background: 'transparent', border: 'none', color: 'var(--astrovox-text-muted)', cursor: 'pointer', padding: '2px' }}><Icon name="x" size={10} /></button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
