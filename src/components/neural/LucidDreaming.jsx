import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { lucidStart, lucidTick } from '../../services/neuralService'

const NEURAL_COLORS = {
  primary: '#06b6d4',
  secondary: '#8b5cf6',
  accent: '#22d3ee',
  cardBackground: 'rgba(6, 182, 212, 0.08)',
  border: 'rgba(6, 182, 212, 0.25)',
  text: '#e5e7eb',
  muted: '#9ca3af',
}

const PROTOCOL_STEPS = [
  'mILD_induction',
  'reality_check',
  'stabilization_cue',
  'intention_setting',
  'wake_back_to_bed',
]

export function LucidDreamingProtocol({ className = '', style = {} }) {
  const [active, setActive] = useState(false)
  const [attempts, setAttempts] = useState(0)
  const [currentReading, setCurrentReading] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const toggleProtocol = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await lucidStart(!active)
      setActive(res.active)
      setAttempts(res.attempts || 0)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [active])

  const tick = useCallback(async () => {
    if (!active) return
    setLoading(true)
    try {
      const res = await lucidTick([], [])
      if (res.reading) {
        setCurrentReading(res.reading)
        setAttempts(res.attempts || 0)
      }
      if (!res.active) setActive(false)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [active])

  useEffect(() => {
    if (!active) return
    const interval = setInterval(tick, 4000)
    return () => clearInterval(interval)
  }, [active, tick])

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
        Lucid Dreaming Protocol
      </h3>
      <p style={{ margin: '0 0 16px 0', color: NEURAL_COLORS.muted, fontSize: '13px' }}>
        Guided protocol for lucid dream induction and stabilization.
      </p>

      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', alignItems: 'center' }}>
        <button
          onClick={toggleProtocol}
          disabled={loading}
          style={{
            background: active
              ? `linear-gradient(135deg, #ef444440, #ef444420)`
              : `linear-gradient(135deg, ${NEURAL_COLORS.primary}40, ${NEURAL_COLORS.primary}20)`,
            border: `1px solid ${active ? '#ef444460' : NEURAL_COLORS.primary + '60'}`,
            borderRadius: '8px',
            padding: '8px 16px',
            color: active ? '#f87171' : NEURAL_COLORS.accent,
            fontSize: '13px',
            fontWeight: 500,
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? 'Processing...' : active ? 'Stop Protocol' : 'Start Protocol'}
        </button>
        <div style={{ color: NEURAL_COLORS.muted, fontSize: '12px' }}>
          Attempts: <strong style={{ color: NEURAL_COLORS.text }}>{attempts}</strong>
        </div>
        <div style={{
          marginLeft: 'auto',
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          background: active ? '#10b981' : NEURAL_COLORS.muted,
          boxShadow: active ? `0 0 8px #10b981` : 'none',
        }} />
      </div>

      {error && (
        <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '12px' }}>
          {error}
        </div>
      )}

      <div style={{ marginBottom: '16px' }}>
        <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '8px' }}>Protocol Steps</div>
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          {PROTOCOL_STEPS.map((step, i) => (
            <span
              key={step}
              style={{
                background: active ? `${NEURAL_COLORS.primary}20` : 'rgba(0,0,0,0.2)',
                border: `1px solid ${active ? NEURAL_COLORS.primary + '40' : NEURAL_COLORS.border}`,
                borderRadius: '999px',
                padding: '4px 10px',
                fontSize: '11px',
                color: active ? NEURAL_COLORS.accent : NEURAL_COLORS.muted,
              }}
            >
              {step.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      </div>

      {currentReading && (
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          style={{
            background: 'rgba(0,0,0,0.25)',
            border: `1px solid ${NEURAL_COLORS.border}`,
            borderRadius: '12px',
            padding: '16px',
          }}
        >
          <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: '120px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Stage</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600 }}>
                {currentReading.hypnogram_stage}
              </div>
            </div>
            <div style={{ flex: 1, minWidth: '120px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Lucid Readiness</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600 }}>
                {(currentReading.lucid_dream_readiness * 100).toFixed(0)}%
              </div>
            </div>
            <div style={{ flex: 1, minWidth: '120px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Clarity</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600 }}>
                {(currentReading.dream_clarity * 100).toFixed(0)}%
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
