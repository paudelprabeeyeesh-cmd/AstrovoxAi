import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { motorImageryCommand, motorImageryHistory } from '../../services/neuralService'

const NEURAL_COLORS = {
  primary: '#06b6d4',
  secondary: '#8b5cf6',
  accent: '#22d3ee',
  cardBackground: 'rgba(6, 182, 212, 0.08)',
  border: 'rgba(6, 182, 212, 0.25)',
  text: '#e5e7eb',
  muted: '#9ca3af',
}

const COMMANDS = [
  'left_hand', 'right_hand', 'feet', 'tongue', 'rest',
  'turn_left', 'turn_right', 'forward', 'backward',
]

export function MotorImagery({ className = '', style = {} }) {
  const [history, setHistory] = useState([])
  const [predicted, setPredicted] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    motorImageryHistory(20).then((res) => {
      setHistory(res.history || [])
    }).catch(() => {})
  }, [])

  const predict = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await motorImageryCommand([], [])
      setPredicted(res.command)
      setHistory((prev) => [res.command, ...prev].slice(0, 50))
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
        Motor Imagery Command System
      </h3>
      <p style={{ margin: '0 0 16px 0', color: NEURAL_COLORS.muted, fontSize: '13px' }}>
        Decode motor imagery into control commands from EEG epochs.
      </p>

      <button
        onClick={predict}
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
        {loading ? 'Decoding...' : 'Predict Command'}
      </button>

      {error && (
        <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '12px' }}>
          {error}
        </div>
      )}

      {predicted && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          style={{
            background: 'rgba(0,0,0,0.25)',
            border: `1px solid ${NEURAL_COLORS.border}`,
            borderRadius: '12px',
            padding: '16px',
            marginBottom: '16px',
          }}
        >
          <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '6px' }}>
            Latest Prediction
          </div>
          <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: '120px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Command</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600, textTransform: 'uppercase' }}>
                {predicted.predicted_class}
              </div>
            </div>
            <div style={{ flex: 1, minWidth: '120px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Confidence</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600 }}>
                {(predicted.confidence * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </motion.div>
      )}

      <div>
        <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '8px' }}>
          Command History ({history.length})
        </div>
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          {history.slice(0, 20).map((cmd, i) => (
            <span
              key={i}
              style={{
                background: `${NEURAL_COLORS.primary}20`,
                border: `1px solid ${NEURAL_COLORS.primary}40`,
                borderRadius: '999px',
                padding: '3px 8px',
                fontSize: '11px',
                color: NEURAL_COLORS.accent,
                opacity: 1 - i * 0.03,
              }}
            >
              {cmd.predicted_class}
            </span>
          ))}
        </div>
      </div>
    </motion.div>
  )
}
