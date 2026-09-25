import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { neurofeedbackMetrics, getRecentEpochs } from '../../services/neuralService'

const NEURAL_COLORS = {
  primary: '#06b6d4',
  secondary: '#8b5cf6',
  accent: '#22d3ee',
  cardBackground: 'rgba(6, 182, 212, 0.08)',
  border: 'rgba(6, 182, 212, 0.25)',
  text: '#e5e7eb',
  muted: '#9ca3af',
}

const BAND_COLORS = {
  delta: '#3b82f6',
  theta: '#8b5cf6',
  alpha: '#06b6d4',
  beta: '#10b981',
  gamma: '#f59e0b',
}

export function Neurofeedback({ className = '', style = {} }) {
  const [metrics, setMetrics] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadMetrics = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await neurofeedbackMetrics()
      setMetrics(res.metrics || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadMetrics()
    const interval = setInterval(loadMetrics, 3000)
    return () => clearInterval(interval)
  }, [loadMetrics])

  const bandMetrics = metrics.reduce((acc, m) => {
    const band = m.metric.replace('_power', '')
    if (!acc[band]) acc[band] = []
    acc[band].push(m)
    return acc
  }, {})

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        background: NEURAL_COLORS.cardBackground,
        border: `1px solid ${NEURAL_COLORS.border}`,
        borderRadius: '16px',
        padding: '24px',
        backdropFilter: 'blur(12px)',
        ...style,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h3 style={{ margin: 0, color: NEURAL_COLORS.accent, fontSize: '18px', fontWeight: 600 }}>
            Neurofeedback Dashboard
          </h3>
          <p style={{ margin: '4px 0 0', color: NEURAL_COLORS.muted, fontSize: '13px' }}>
            Real-time band power monitoring
          </p>
        </div>
        <button
          onClick={loadMetrics}
          disabled={loading}
          style={{
            background: `${NEURAL_COLORS.primary}20`,
            border: `1px solid ${NEURAL_COLORS.primary}40`,
            borderRadius: '8px',
            padding: '6px 12px',
            color: NEURAL_COLORS.text,
            fontSize: '12px',
            cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '12px' }}>
          {error}
        </div>
      )}

      {Object.keys(bandMetrics).length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {Object.entries(bandMetrics).map(([band, items]) => {
            const avg = items.reduce((sum, m) => sum + (m.value || 0), 0) / items.length
            const max = Math.max(...items.map((m) => m.value || 0), 0.01)
            return (
              <div key={band} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ width: '50px', fontSize: '11px', color: NEURAL_COLORS.muted, textTransform: 'capitalize' }}>
                  {band}
                </div>
                <div style={{ flex: 1, height: '8px', background: 'rgba(0,0,0,0.3)', borderRadius: '999px', overflow: 'hidden' }}>
                  <motion.div
                    animate={{ width: `${Math.min(100, (avg / max) * 100)}%` }}
                    transition={{ duration: 0.5 }}
                    style={{
                      height: '100%',
                      background: BAND_COLORS[band] || NEURAL_COLORS.primary,
                      borderRadius: '999px',
                    }}
                  />
                </div>
                <div style={{ width: '60px', textAlign: 'right', fontSize: '12px', color: NEURAL_COLORS.text }}>
                  {avg.toFixed(3)}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div style={{ color: NEURAL_COLORS.muted, fontSize: '13px' }}>
          No neurofeedback metrics available yet.
        </div>
      )}
    </motion.div>
  )
}
