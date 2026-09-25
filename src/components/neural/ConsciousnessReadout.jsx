import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { consciousnessReadout, consciousnessHistory } from '../../services/neuralService'

const NEURAL_COLORS = {
  primary: '#06b6d4',
  secondary: '#8b5cf6',
  accent: '#22d3ee',
  cardBackground: 'rgba(6, 182, 212, 0.08)',
  border: 'rgba(6, 182, 212, 0.25)',
  text: '#e5e7eb',
  muted: '#9ca3af',
}

export function ConsciousnessReadout({ className = '', style = {} }) {
  const [readout, setReadout] = useState(null)
  const [history, setHistory] = useState([])
  const [selfClarity, setSelfClarity] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    consciousnessHistory(20).then((res) => {
      setHistory(res.history || [])
    }).catch(() => {})
  }, [])

  const generate = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await consciousnessReadout([], [], selfClarity)
      setReadout(res.readout)
      setHistory((prev) => [res.readout, ...prev].slice(0, 50))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [selfClarity])

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
        Consciousness Readout Visualization
      </h3>
      <p style={{ margin: '0 0 16px 0', color: NEURAL_COLORS.muted, fontSize: '13px' }}>
        P300, ERP, band power, and metacognition metrics.
      </p>

      <div style={{ marginBottom: '12px', display: 'flex', gap: '12px', alignItems: 'center' }}>
        <label style={{ color: NEURAL_COLORS.muted, fontSize: '12px' }}>Self-reported clarity</label>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={selfClarity ?? 0.5}
          onChange={(e) => setSelfClarity(parseFloat(e.target.value))}
          style={{ flex: 1 }}
        />
        <span style={{ color: NEURAL_COLORS.text, fontSize: '12px', width: '40px', textAlign: 'right' }}>
          {((selfClarity ?? 0.5) * 100).toFixed(0)}%
        </span>
      </div>

      <button
        onClick={generate}
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
        {loading ? 'Generating...' : 'Generate Readout'}
      </button>

      {error && (
        <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '12px' }}>
          {error}
        </div>
      )}

      {readout && (
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
            <div style={{ flex: 1, minWidth: '120px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>P300 Detected</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600 }}>
                {readout.p300_detected ? 'Yes' : 'No'}
              </div>
            </div>
            <div style={{ flex: 1, minWidth: '120px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>P300 Latency</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600 }}>
                {readout.p300_latency_ms ? `${readout.p300_latency_ms.toFixed(1)} ms` : 'N/A'}
              </div>
            </div>
            <div style={{ flex: 1, minWidth: '120px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Integrated Awareness</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600 }}>
                {(readout.integrated_awareness * 100).toFixed(0)}%
              </div>
            </div>
          </div>

          <div style={{ marginBottom: '12px' }}>
            <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '6px' }}>ERP Components</div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {Object.entries(readout.erp_components || {}).map(([name, value]) => (
                <span
                  key={name}
                  style={{
                    background: `${NEURAL_COLORS.primary}20`,
                    border: `1px solid ${NEURAL_COLORS.primary}40`,
                    borderRadius: '999px',
                    padding: '3px 8px',
                    fontSize: '11px',
                    color: NEURAL_COLORS.accent,
                  }}
                >
                  {name}: {(value * 100).toFixed(0)}%
                </span>
              ))}
            </div>
          </div>

          <div>
            <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '6px' }}>Metacognition / Working Memory</div>
            <div style={{ display: 'flex', gap: '16px' }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '11px', color: NEURAL_COLORS.muted, marginBottom: '4px' }}>Metacognition</div>
                <div style={{ height: '6px', background: 'rgba(0,0,0,0.3)', borderRadius: '999px', overflow: 'hidden' }}>
                  <motion.div
                    animate={{ width: `${readout.metacognition * 100}%` }}
                    style={{ height: '100%', background: NEURAL_COLORS.primary, borderRadius: '999px' }}
                  />
                </div>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '11px', color: NEURAL_COLORS.muted, marginBottom: '4px' }}>Working Memory Load</div>
                <div style={{ height: '6px', background: 'rgba(0,0,0,0.3)', borderRadius: '999px', overflow: 'hidden' }}>
                  <motion.div
                    animate={{ width: `${readout.working_memory_load * 100}%` }}
                    style={{ height: '100%', background: NEURAL_COLORS.secondary, borderRadius: '999px' }}
                  />
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
