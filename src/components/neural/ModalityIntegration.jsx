import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { modalityAcquire, modalityStatus } from '../../services/neuralService'

const NEURAL_COLORS = {
  primary: '#06b6d4',
  secondary: '#8b5cf6',
  accent: '#22d3ee',
  cardBackground: 'rgba(6, 182, 212, 0.08)',
  border: 'rgba(6, 182, 212, 0.25)',
  text: '#e5e7eb',
  muted: '#9ca3af',
}

const MODALITIES = ['eeg', 'emg', 'meg', 'eog', 'ecg']

export function ModalityIntegration({ className = '', style = {} }) {
  const [modality, setModality] = useState('eeg')
  const [channels, setChannels] = useState([])
  const [sampleRate, setSampleRate] = useState(250)
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const acquire = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await modalityAcquire(modality, channels, sampleRate)
      setStatus(res.acquisition)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [modality, channels, sampleRate])

  const checkStatus = useCallback(async () => {
    try {
      const res = await modalityStatus(modality)
      setStatus(res.modality_status)
    } catch {}
  }, [modality])

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
        EEG / EMG / MEG Integration Stubs
      </h3>
      <p style={{ margin: '0 0 16px 0', color: NEURAL_COLORS.muted, fontSize: '13px' }}>
        Acquire and monitor neural signal modalities.
      </p>

      <div style={{ marginBottom: '12px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        <select
          value={modality}
          onChange={(e) => setModality(e.target.value)}
          style={{
            background: 'rgba(0,0,0,0.3)',
            border: `1px solid ${NEURAL_COLORS.border}`,
            borderRadius: '8px',
            padding: '8px 12px',
            color: NEURAL_COLORS.text,
            fontSize: '13px',
          }}
        >
          {MODALITIES.map((m) => (
            <option key={m} value={m}>{m.toUpperCase()}</option>
          ))}
        </select>
        <input
          type="number"
          value={sampleRate}
          onChange={(e) => setSampleRate(parseInt(e.target.value || '250', 10))}
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
        <input
          value={channels.join(', ')}
          onChange={(e) => setChannels(e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
          placeholder="Channels (comma-separated)"
          style={{
            flex: 1,
            background: 'rgba(0,0,0,0.3)',
            border: `1px solid ${NEURAL_COLORS.border}`,
            borderRadius: '8px',
            padding: '8px 12px',
            color: NEURAL_COLORS.text,
            fontSize: '13px',
          }}
        />
      </div>

      <div style={{ marginBottom: '16px', display: 'flex', gap: '8px' }}>
        <button
          onClick={acquire}
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
          }}
        >
          {loading ? 'Acquiring...' : 'Acquire'}
        </button>
        <button
          onClick={checkStatus}
          style={{
            background: `${NEURAL_COLORS.secondary}20`,
            border: `1px solid ${NEURAL_COLORS.secondary}40`,
            borderRadius: '8px',
            padding: '8px 16px',
            color: NEURAL_COLORS.text,
            fontSize: '13px',
            cursor: 'pointer',
          }}
        >
          Check Status
        </button>
      </div>

      {error && (
        <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '12px' }}>
          {error}
        </div>
      )}

      {status && (
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
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Modality</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600, textTransform: 'uppercase' }}>
                {status.modality}
              </div>
            </div>
            <div style={{ flex: 1, minWidth: '120px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Channels</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600 }}>
                {status.channels?.length || 0}
              </div>
            </div>
            <div style={{ flex: 1, minWidth: '120px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Sample Rate</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600 }}>
                {status.sample_rate_hz} Hz
              </div>
            </div>
            <div style={{ flex: 1, minWidth: '120px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Unit</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600 }}>
                {status.unit}
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
