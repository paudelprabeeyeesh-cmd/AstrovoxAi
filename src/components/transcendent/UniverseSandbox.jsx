import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { createUniverse, listUniverses, runSimulation, destroyUniverse } from '../../services/sandboxService'

export default function UniverseSandbox() {
  const [universes, setUniverses] = useState([])
  const [newName, setNewName] = useState('')
  const [simulating, setSimulating] = useState(null)
  const [events, setEvents] = useState({})

  useEffect(() => {
    loadUniverses()
  }, [])

  const loadUniverses = async () => {
    try {
      const data = await listUniverses()
      setUniverses(data.universes || [])
    } catch (e) {
      console.error('Failed to load universes:', e)
    }
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!newName.trim()) return
    try {
      await createUniverse(newName, { gravity: 1.0, time_dilation: 1.0 })
      setNewName('')
      loadUniverses()
    } catch (e) {
      console.error('Failed to create universe:', e)
    }
  }

  const handleSimulate = async (universeId) => {
    setSimulating(universeId)
    try {
      const data = await runSimulation(universeId, 5)
      setEvents(prev => ({ ...prev, [universeId]: data.events || [] }))
    } catch (e) {
      console.error('Simulation failed:', e)
    } finally {
      setSimulating(null)
    }
  }

  const handleDestroy = async (universeId) => {
    try {
      await destroyUniverse(universeId)
      loadUniverses()
      setEvents(prev => {
        const next = { ...prev }
        delete next[universeId]
        return next
      })
    } catch (e) {
      console.error('Failed to destroy universe:', e)
    }
  }

  return (
    <div style={{
      backgroundColor: 'rgba(4,8,20,0.6)',
      border: '1px solid #1e293b',
      borderRadius: '12px',
      padding: '16px',
      height: '100%',
      overflow: 'auto'
    }}>
      <h3 style={{
        margin: '0 0 12px',
        fontSize: '13px',
        color: '#f59e0b',
        textTransform: 'uppercase',
        letterSpacing: '1px'
      }}>
        📦 Universe-in-a-Box Sandbox
      </h3>

      <form onSubmit={handleCreate} style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New universe name..."
          style={{
            flex: 1,
            padding: '6px 10px',
            background: 'var(--astrovox-surface)',
            border: '1px solid var(--astrovox-border)',
            borderRadius: '6px',
            color: 'var(--astrovox-text)',
            fontSize: '12px',
            outline: 'none'
          }}
        />
        <button type="submit" style={{
          padding: '6px 12px',
          background: '#f59e0b',
          border: 'none',
          borderRadius: '6px',
          color: '#02040a',
          fontSize: '11px',
          fontWeight: 700,
          cursor: 'pointer'
        }}>
          Create
        </button>
      </form>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {universes.map((u) => (
          <motion.div
            key={u.universe_id}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            style={{
              padding: '12px',
              backgroundColor: 'rgba(6,182,212,0.05)',
              border: '1px solid #1e293b',
              borderRadius: '8px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <div>
                <div style={{ fontSize: '13px', color: '#e2e8f0', fontWeight: 600 }}>{u.name}</div>
                <div style={{ fontSize: '10px', color: '#64748b' }}>
                  Events: {u.events_count} · {u.is_running ? 'Running' : 'Idle'}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '4px' }}>
                <button
                  onClick={() => handleSimulate(u.universe_id)}
                  disabled={simulating === u.universe_id}
                  style={{
                    padding: '4px 8px',
                    background: simulating === u.universe_id ? '#64748b' : '#06b6d4',
                    border: 'none',
                    borderRadius: '4px',
                    color: '#02040a',
                    fontSize: '10px',
                    fontWeight: 600,
                    cursor: simulating === u.universe_id ? 'not-allowed' : 'pointer'
                  }}
                >
                  {simulating === u.universe_id ? 'Running...' : 'Simulate'}
                </button>
                <button
                  onClick={() => handleDestroy(u.universe_id)}
                  style={{
                    padding: '4px 8px',
                    background: '#ef4444',
                    border: 'none',
                    borderRadius: '4px',
                    color: '#fff',
                    fontSize: '10px',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  Destroy
                </button>
              </div>
            </div>

            <AnimatePresence>
              {events[u.universe_id] && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  style={{ marginTop: '8px' }}
                >
                  <div style={{ fontSize: '10px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '4px' }}>
                    Simulation Events
                  </div>
                  {events[u.universe_id].map((event, idx) => (
                    <div key={idx} style={{
                      padding: '4px 8px',
                      backgroundColor: 'rgba(6,182,212,0.03)',
                      borderRadius: '4px',
                      fontSize: '10px',
                      color: '#94a3b8',
                      fontFamily: 'monospace',
                      marginBottom: '2px'
                    }}>
                      Step {event.step}: {event.type}
                    </div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
