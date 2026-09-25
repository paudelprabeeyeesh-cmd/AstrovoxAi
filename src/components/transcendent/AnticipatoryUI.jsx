import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'

export default function AnticipatoryUI({ userId, interface = 'chat', context = {} }) {
  const [adjustments, setAdjustments] = useState([])
  const [applied, setApplied] = useState(false)

  useEffect(() => {
    if (!userId) return
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`/omniscient/ui/adjustments?user_id=${userId}&interface=${interface}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ context }),
        })
        if (res.ok) {
          const data = await res.json()
          setAdjustments(data.adjustments || [])
        }
      } catch (e) {
        console.error('Anticipatory UI failed:', e)
      }
    }, 2000)
    return () => clearTimeout(timer)
  }, [userId, interface, context])

  const applyAdjustment = async (adjustmentId) => {
    try {
      await fetch(`/omniscient/ui/adjustments/${adjustmentId}/apply`, { method: 'POST' })
      setApplied(true)
      setTimeout(() => setApplied(false), 3000)
    } catch (e) {
      console.error('Failed to apply adjustment:', e)
    }
  }

  if (adjustments.length === 0) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        position: 'fixed',
        top: '16px',
        right: '16px',
        zIndex: 9999,
        backgroundColor: 'rgba(4, 8, 20, 0.9)',
        border: '1px solid #f59e0b',
        borderRadius: '12px',
        padding: '12px 16px',
        maxWidth: '300px',
        backdropFilter: 'blur(12px)',
        boxShadow: '0 8px 32px rgba(0,0,0,0.4)'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <span style={{ fontSize: '16px' }}>⚡</span>
        <span style={{ fontSize: '12px', color: '#f59e0b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px' }}>
          Anticipatory Adjustment
        </span>
      </div>
      {adjustments.map((adj) => (
        <div key={adj.adjustment_id} style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '6px 8px',
          backgroundColor: 'rgba(6,182,212,0.05)',
          borderRadius: '6px',
          marginBottom: '4px',
          fontSize: '11px',
          color: '#94a3b8'
        }}>
          <span>{JSON.stringify(adj.adjustments)}</span>
          <span style={{ color: '#f59e0b', fontSize: '10px' }}>
            {(adj.confidence * 100).toFixed(0)}%
          </span>
        </div>
      ))}
      {applied && (
        <div style={{ fontSize: '10px', color: '#22c55e', marginTop: '4px' }}>
          Adjustment applied!
        </div>
      )}
    </motion.div>
  )
}
