import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { signalProcess, getRecentEpochs } from '../../services/neuralService'

const NEURAL_COLORS = {
  primary: '#06b6d4',
  secondary: '#8b5cf6',
  accent: '#22d3ee',
  cardBackground: 'rgba(6, 182, 212, 0.08)',
  border: 'rgba(6, 182, 212, 0.25)',
  text: '#e5e7eb',
  muted: '#9ca3af',
}

export function SignalPipeline({ className = '', style = {} }) {
  const [signal, setSignal] = useState({ samples: [[0.1, 0.2, 0.3]], channels: ['FP1', 'FP2'] })
  const [pipelineId, setPipelineId] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const process = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await signalProcess(signal, pipelineId)
      setResult(res.result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [signal, pipelineId])

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
        Neural Signal Processing Pipeline
      </h3>
      <p style={{ margin: '0 0 16px 0', color: NEURAL_COLORS.muted, fontSize: '13px' }}>
        Notch, band-pass, artifact rejection, and feature extraction.
      </p>

      <div style={{ marginBottom: '12px' }}>
        <label style={{ display: 'block', color: NEURAL_COLORS.muted, fontSize: '12px', marginBottom: '6px' }}>
          Signal JSON
        </label>
        <textarea
          value={JSON.stringify(signal)}
          onChange={(e) => {
            try {
              setSignal(JSON.parse(e.target.value))
            } catch {}
          }}
          rows={4}
          style={{
            width: '100%',
            background: 'rgba(0,0,0,0.3)',
            border: `1px solid ${NEURAL_COLORS.border}`,
            borderRadius: '8px',
            padding: '10px 12px',
            color: NEURAL_COLORS.text,
            fontSize: '13px',
            fontFamily: 'monospace',
            resize: 'vertical',
          }}
        />
      </div>

      <div style={{ marginBottom: '16px' }}>
        <label style={{ display: 'block', color: NEURAL_COLORS.muted, fontSize: '12px', marginBottom: '6px' }}>
          Pipeline ID (optional)
        </label>
        <input
          value={pipelineId}
          onChange={(e) => setPipelineId(e.target.value)}
          style={{
            width: '100%',
            background: 'rgba(0,0,0,0.3)',
            border: `1px solid ${NEURAL_COLORS.border}`,
            borderRadius: '8px',
            padding: '8px 12px',
            color: NEURAL_COLORS.text,
            fontSize: '13px',
          }}
        />
      </div>

      <button
        onClick={process}
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
        {loading ? 'Processing...' : 'Process Signal'}
      </button>

      {error && (
        <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '12px' }}>
          {error}
        </div>
      )}

      {result && (
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
          <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '6px' }}>
            Stages Completed
          </div>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '12px' }}>
            {(result.stages_completed || []).map((stage) => (
              <span
                key={stage}
                style={{
                  background: `${NEURAL_COLORS.primary}20`,
                  border: `1px solid ${NEURAL_COLORS.primary}40`,
                  borderRadius: '999px',
                  padding: '3px 8px',
                  fontSize: '11px',
                  color: NEURAL_COLORS.accent,
                }}
              >
                {stage.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
          <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '6px' }}>Features</div>
          <pre style={{
            background: 'rgba(0,0,0,0.3)',
            borderRadius: '8px',
            padding: '10px',
            color: NEURAL_COLORS.text,
            fontSize: '11px',
            overflow: 'auto',
          }}>
            {JSON.stringify(result.features || {}, null, 2)}
          </pre>
        </motion.div>
      )}
    </motion.div>
  )
}
