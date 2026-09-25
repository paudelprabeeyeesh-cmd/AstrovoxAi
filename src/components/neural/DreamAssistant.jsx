import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { dreamAssist, dreamHistory } from '../../services/neuralService'

const NEURAL_COLORS = {
  primary: '#06b6d4',
  secondary: '#8b5cf6',
  accent: '#22d3ee',
  cardBackground: 'rgba(6, 182, 212, 0.08)',
  border: 'rgba(6, 182, 212, 0.25)',
  text: '#e5e7eb',
  muted: '#9ca3af',
}

const STAGE_COLORS = {
  Wake: '#f59e0b',
  N1: '#06b6d4',
  N2: '#3b82f6',
  N3: '#8b5cf6',
  REM: '#10b981',
}

export function DreamAssistant({ className = '', style = {} }) {
  const [reading, setReading] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    dreamHistory(20).then((res) => {
      setHistory(res.history || [])
    }).catch(() => {})
  }, [])

  const assist = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await dreamAssist([], [])
      setReading(res.reading)
      setHistory((prev) => [res.reading, ...prev].slice(0, 50))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

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
      <h3 style={{ margin: '0 0 16px 0', color: NEURAL_COLORS.accent, fontSize: '18px', fontWeight: 600 }}>
        Dream-State Assistant
      </h3>
      <p style={{ margin: '0 0 16px 0', color: NEURAL_COLORS.muted, fontSize: '13px' }}>
        Monitor sleep stages and dream likelihood.
      </p>

      <button
        onClick={assist}
        disabled={loading}
        style={{
          background: `linear-gradient(135deg, ${NEURAL_COLORS.primary}40, ${NEURAL_COLORS.primary}20)`,
          border: `1px solid ${NEURAL_COLORS.primary}60`,
          borderRadius: '8px',
          padding: '8px 16px',
          color: NEURAL_COLORS.accent,
          fontSize: '13px',
          fontWeight: 500,
          cursor: loading ? 'not-allowed' : 'pointer',
          opacity: loading ? 0.6 : 1,
          marginBottom: '16px',
        }}
      >
        {loading ? 'Analyzing...' : 'Analyze Sleep Stage'}
      </button>

      {error && (
        <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '12px' }}>
          {error}
        </div>
      )}

      {reading && (
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          style={{
            background: 'rgba(0,0,0,0.25)',
            border: `1px solid ${NEURAL_COLORS.border}`,
            borderRadius: '12px',
            padding: '16px',
            marginBottom: '16px',
          }}
        >
          <div style={{ display: 'flex', gap: '16px', marginBottom: '12px', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: '100px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Stage</div>
              <div style={{
                color: STAGE_COLORS[reading.hypnogram_stage] || NEURAL_COLORS.text,
                fontSize: '14px',
                fontWeight: 600,
              }}>
                {reading.hypnogram_stage}
              </div>
            </div>
            <div style={{ flex: 1, minWidth: '100px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>REM Ratio</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600 }}>
                {(reading.rem_sleep_ratio * 100).toFixed(0)}%
              </div>
            </div>
            <div style={{ flex: 1, minWidth: '100px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Dream Likelihood</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600 }}>
                {(reading.dream_likelihood * 100).toFixed(0)}%
              </div>
            </div>
            <div style={{ flex: 1, minWidth: '100px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Clarity</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600 }}>
                {(reading.dream_clarity * 100).toFixed(0)}%
              </div>
            </div>
          </div>
          <div>
            <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '6px' }}>Lucid Dream Readiness</div>
            <div style={{ height: '6px', background: 'rgba(0,0,0,0.3)', borderRadius: '999px', overflow: 'hidden' }}>
              <motion.div
                animate={{ width: `${reading.lucid_dream_readiness * 100}%` }}
                transition={{ duration: 0.5 }}
                style={{
                  height: '100%',
                  background: `linear-gradient(90deg, ${NEURAL_COLORS.primary}, ${NEURAL_COLORS.secondary})`,
                  borderRadius: '999px',
                }}
              />
            </div>
          </div>
        </motion.div>
      )}

      <div>
        <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '8px' }}>
          Recent Readings ({history.length})
        </div>
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          {history.slice(0, 15).map((r, i) => (
            <span
              key={r.reading_id || i}
              style={{
                background: `${STAGE_COLORS[r.hypnogram_stage] || NEURAL_COLORS.primary}20`,
                border: `1px solid ${STAGE_COLORS[r.hypnogram_stage] || NEURAL_COLORS.primary}40`,
                borderRadius: '999px',
                padding: '3px 8px',
                fontSize: '11px',
                color: NEURAL_COLORS.text,
                opacity: 1 - i * 0.03,
              }}
            >
              {r.hypnogram_stage}
            </span>
          ))}
        </div>
      </div>
    </motion.div>
  )
}
