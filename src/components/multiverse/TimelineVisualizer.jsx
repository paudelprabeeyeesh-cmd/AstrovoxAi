import { useState, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { getUniverseMessages, sendUniverseMessage } from '../../services/multiverseService'

export default function TimelineVisualizer({ universeId, onBack }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!universeId) return
    setLoading(true)
    setError(null)
    getUniverseMessages(universeId, 200, 0)
      .then((data) => setMessages(data.messages || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [universeId])

  async function handleSend(e) {
    e.preventDefault()
    if (!input.trim() || sending) return
    setSending(true)
    setError(null)
    try {
      const res = await sendUniverseMessage(universeId, input.trim(), 'user')
      setMessages((prev) => [...prev, res.message])
      setInput('')
    } catch (err) {
      setError(err.message)
    } finally {
      setSending(false)
    }
  }

  const timeline = useMemo(() => {
    const points = messages.map((m, idx) => ({ ...m, index: idx }))
    return points
  }, [messages])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '12px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {onBack && (
          <button onClick={onBack} style={{ padding: '6px 12px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '6px', color: '#94a3b8', cursor: 'pointer', fontSize: '11px', fontFamily: 'inherit' }}>
            ← Back
          </button>
        )}
        <h3 style={{ margin: 0, fontSize: '14px', color: '#67e8f9' }}>Timeline Visualizer</h3>
        <span style={{ marginLeft: 'auto', fontSize: '10px', color: '#475569' }}>{messages.length} events</span>
      </div>

      {error && (
        <div style={{ padding: '10px', backgroundColor: 'rgba(239,68,68,0.1)', border: '1px solid #ef4444', borderRadius: '6px', fontSize: '11px', color: '#f87171' }}>
          ⚠️ {error}
        </div>
      )}

      <div style={{ flex: 1, overflowY: 'auto', padding: '12px', display: 'flex', flexDirection: 'column', gap: '8px', backgroundColor: 'rgba(4,8,20,0.3)', border: '1px solid #1e293b', borderRadius: '8px' }}>
        {loading && <div style={{ color: '#64748b', fontSize: '12px', textAlign: 'center', padding: '20px' }}>Loading timeline...</div>}
        {!loading && timeline.length === 0 && <div style={{ color: '#475569', fontSize: '12px', textAlign: 'center', padding: '20px' }}>No events recorded in this universe.</div>}
        <AnimatePresence>
          {timeline.map((event, idx) => (
            <motion.div key={event.id || idx} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: idx * 0.02 }} style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: '32px' }}>
                <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: event.role === 'user' ? '#06b6d4' : event.role === 'system' ? '#fbbf24' : '#a78bfa', marginTop: '4px' }} />
                {idx < timeline.length - 1 && <div style={{ width: '2px', flex: 1, backgroundColor: '#1e293b', minHeight: '20px' }} />}
              </div>
              <div style={{ flex: 1, padding: '8px 12px', backgroundColor: 'rgba(30,41,59,0.5)', border: '1px solid #1e293b', borderRadius: '6px', fontSize: '12px', color: '#cbd5e1', lineHeight: '1.5' }}>
                <div style={{ fontSize: '10px', color: '#64748b', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{event.role} · {new Date(event.created_at).toLocaleTimeString()}</div>
                {event.content}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      <form onSubmit={handleSend} style={{ display: 'flex', gap: '8px' }}>
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Send message to this universe..." disabled={sending} style={{ flex: 1, padding: '10px 14px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#67e8f9', fontSize: '12px', fontFamily: 'inherit', outline: 'none' }} onFocus={(e) => e.target.style.borderColor = '#06b6d4'} onBlur={(e) => e.target.style.borderColor = '#1e293b'} />
        <button type="submit" disabled={sending || !input.trim()} style={{ padding: '10px 18px', backgroundColor: '#06b6d4', color: '#02040a', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '700', fontSize: '12px', opacity: sending || !input.trim() ? 0.5 : 1 }}>
          SEND
        </button>
      </form>
    </div>
  )
}
