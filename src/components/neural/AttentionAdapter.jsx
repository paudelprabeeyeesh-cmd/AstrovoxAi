import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { attentionAdapt, getRecentEpochs } from '../../services/neuralService'

const NEURAL_COLORS = {
  primary: '#06b6d4',
  secondary: '#8b5cf6',
  accent: '#22d3ee',
  cardBackground: 'rgba(6, 182, 212, 0.08)',
  border: 'rgba(6, 182, 212, 0.25)',
  text: '#e5e7eb',
  muted: '#9ca3af',
}

export function AttentionAdapter({ className = '', style = {}, onAdaptationChange }) {
  const [focusScore, setFocusScore] = useState(0.5)
  const [distractionSignals, setDistractionSignals] = useState([])
  const [uiContext, setUiContext] = useState({ timestamp: Date.now() })
  const [adaptation, setAdaptation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const adapt = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await attentionAdapt(focusScore, distractionSignals, uiContext)
      setAdaptation(res.adaptation)
      onAdaptationChange?.(res.adaptation)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [focusScore, distractionSignals, uiContext, onAdaptationChange])

  const addDistraction = useCallback(() => {
    setDistractionSignals((prev) => [
      ...prev,
      { type: 'notification', intensity: Math.random() * 0.8, timestamp: Date.now() },
    ])
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
        Attention-Aware UI Adapter
      </h3>
      <p style={{ margin: '0 0 16px 0', color: NEURAL_COLORS.muted, fontSize: '13px' }}>
        Dynamically adjust UI based on attention state.
      </p>

      <div style={{ marginBottom: '12px' }}>
        <label style={{ display: 'block', color: NEURAL_COLORS.muted, fontSize: '12px', marginBottom: '6px' }}>
          Focus Score: {(focusScore * 100).toFixed(0)}%
        </label>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={focusScore}
          onChange={(e) => setFocusScore(parseFloat(e.target.value))}
          style={{ width: '100%' }}
        />
      </div>

      <div style={{ marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
        <button
          onClick={addDistraction}
          style={{
            background: `${NEURAL_COLORS.secondary}20`,
            border: `1px solid ${NEURAL_COLORS.secondary}40`,
            borderRadius: '8px',
            padding: '6px 12px',
            color: NEURAL_COLORS.text,
            fontSize: '12px',
            cursor: 'pointer',
          }}
        >
          Add Distraction Signal
        </button>
        <span style={{ color: NEURAL_COLORS.muted, fontSize: '11px' }}>
          {distractionSignals.length} distraction(s)
        </span>
      </div>

      <button
        onClick={adapt}
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
        {loading ? 'Adapting...' : 'Adapt UI'}
      </button>

      {error && (
        <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '12px' }}>
          {error}
        </div>
      )}

      {adaptation && (
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
          <div style={{ display: 'flex', gap: '12px', marginBottom: '12px', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: '120px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Mode</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600, textTransform: 'capitalize' }}>
                {adaptation.mode.replace('_', ' ')}
              </div>
            </div>
            <div style={{ flex: 1, minWidth: '120px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Effective Focus</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600 }}>
                {(adaptation.effective_focus * 100).toFixed(0)}%
              </div>
            </div>
            <div style={{ flex: 1, minWidth: '120px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Notifications</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600, textTransform: 'capitalize' }}>
                {adaptation.ui_adjustments.notification_mode.replace('_', ' ')}
              </div>
            </div>
          </div>
          <div style={{ marginBottom: '12px' }}>
            <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '6px' }}>UI Adjustments</div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {Object.entries(adaptation.ui_adjustments).map(([key, value]) => (
                <span
                  key={key}
                  style={{
                    background: `${NEURAL_COLORS.primary}20`,
                    border: `1px solid ${NEURAL_COLORS.primary}40`,
                    borderRadius: '999px',
                    padding: '3px 8px',
                    fontSize: '11px',
                    color: NEURAL_COLORS.accent,
                  }}
                >
                  {key}: {typeof value === 'boolean' ? (value ? 'on' : 'off') : value}
                </span>
              ))}
            </div>
          </div>
          <div>
            <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '6px' }}>Suggestions</div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {adaptation.suggestions.map((s, i) => (
                <span
                  key={i}
                  style={{
                    background: `${NEURAL_COLORS.secondary}20`,
                    border: `1px solid ${NEURAL_COLORS.secondary}40`,
                    borderRadius: '999px',
                    padding: '4px 10px',
                    fontSize: '11px',
                    color: NEURAL_COLORS.text,
                  }}
                >
                  {s.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
