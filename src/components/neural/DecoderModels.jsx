import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { brainBridgeCommand, brainBridgeStatus } from '../../services/neuralService'

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
  'open_app', 'close_app', 'scroll', 'click', 'type',
  'volume_up', 'volume_down', 'home', 'back', 'confirm',
]

export function BrainBridge({ className = '', style = {} }) {
  const [command, setCommand] = useState('scroll')
  const [parameters, setParameters] = useState({ direction: 'down', amount: 3, confidence: 0.9 })
  const [threshold, setThreshold] = useState(0.7)
  const [result, setResult] = useState(null)
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    brainBridgeStatus().then((res) => {
      setStatus(res.bridge_status)
    }).catch(() => {})
  }, [])

  const execute = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await brainBridgeCommand(command, parameters, threshold)
      setResult(res.execution)
      setStatus((prev) => ({
        ...prev,
        execution_count: (prev?.execution_count || 0) + 1,
        recent_commands: [res.execution, ...(prev?.recent_commands || [])].slice(0, 10),
      }))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [command, parameters, threshold])

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
        Brain-to-Computer Command Bridge
      </h3>
      <p style={{ margin: '0 0 16px 0', color: NEURAL_COLORS.muted, fontSize: '13px' }}>
        Execute system commands directly from neural intent.
      </p>

      <div style={{ marginBottom: '12px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        <select
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          style={{
            flex: 1,
            minWidth: '160px',
            background: 'rgba(0,0,0,0.3)',
            border: `1px solid ${NEURAL_COLORS.border}`,
            borderRadius: '8px',
            padding: '8px 12px',
            color: NEURAL_COLORS.text,
            fontSize: '13px',
          }}
        >
          {COMMANDS.map((c) => (
            <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>
          ))}
        </select>
        <input
          type="number"
          min={0}
          max={1}
          step={0.05}
          value={threshold}
          onChange={(e) => setThreshold(parseFloat(e.target.value || '0.7'))}
          style={{
            width: '80px',
            background: 'rgba(0,0,0,0.3)',
            border: `1px solid ${NEURAL_COLORS.border}`,
            borderRadius: '8px',
            padding: '8px 12px',
            color: NEURAL_COLORS.text,
            fontSize: '13px',
          }}
        />
      </div>

      <div style={{ marginBottom: '16px' }}>
        <label style={{ display: 'block', color: NEURAL_COLORS.muted, fontSize: '12px', marginBottom: '6px' }}>
          Parameters (JSON)
        </label>
        <textarea
          value={JSON.stringify(parameters)}
          onChange={(e) => {
            try {
              setParameters(JSON.parse(e.target.value))
            } catch {}
          }}
          rows={3}
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

      <button
        onClick={execute}
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
        {loading ? 'Executing...' : 'Execute Command'}
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
            border: `1px solid ${result.status === 'executed' ? '#10b98140' : '#ef444440'}`,
            borderRadius: '12px',
            padding: '16px',
            marginBottom: '16px',
          }}
        >
          <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: '120px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Command</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600, textTransform: 'uppercase' }}>
                {result.command}
              </div>
            </div>
            <div style={{ flex: 1, minWidth: '120px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Status</div>
              <div style={{
                color: result.status === 'executed' ? '#10b981' : result.status === 'rejected' ? '#f59e0b' : '#ef4444',
                fontSize: '14px',
                fontWeight: 600,
                textTransform: 'capitalize',
              }}>
                {result.status}
              </div>
            </div>
            <div style={{ flex: 1, minWidth: '120px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Confidence</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600 }}>
                {((result.confidence || 0) * 100).toFixed(0)}%
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {status && (
        <div>
          <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '8px' }}>
            Bridge Status | Executions: {status.execution_count}
          </div>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {(status.recent_commands || []).slice(0, 8).map((cmd, i) => (
              <span
                key={i}
                style={{
                  background: `${cmd.status === 'executed' ? '#10b981' : '#f59e0b'}20`,
                  border: `1px solid ${cmd.status === 'executed' ? '#10b98140' : '#f59e0b40'}`,
                  borderRadius: '999px',
                  padding: '3px 8px',
                  fontSize: '11px',
                  color: NEURAL_COLORS.text,
                  opacity: 1 - i * 0.03,
                }}
              >
                {cmd.command}
              </span>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  )
}
