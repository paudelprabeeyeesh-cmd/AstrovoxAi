import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { emotionToUI, getCurrentEmotion } from '../../services/neuralService'

const NEURAL_COLORS = {
  primary: '#06b6d4',
  secondary: '#8b5cf6',
  accent: '#22d3ee',
  cardBackground: 'rgba(6, 182, 212, 0.08)',
  border: 'rgba(6, 182, 212, 0.25)',
  text: '#e5e7eb',
  muted: '#9ca3af',
}

export function EmotionMapper({ className = '', style = {}, onMappingChange }) {
  const [valence, setValence] = useState(0.0)
  const [arousal, setArousal] = useState(0.0)
  const [context, setContext] = useState({})
  const [mapping, setMapping] = useState(null)
  const [recentEmotion, setRecentEmotion] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    getCurrentEmotion().then((res) => {
      if (res.emotion) setRecentEmotion(res.emotion)
    }).catch(() => {})
  }, [])

  const map = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await emotionToUI(valence, arousal, context)
      setMapping(res.mapping)
      onMappingChange?.(res.mapping)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [valence, arousal, context, onMappingChange])

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
        Emotion-to-UI Mapper
      </h3>
      <p style={{ margin: '0 0 16px 0', color: NEURAL_COLORS.muted, fontSize: '13px' }}>
        Map emotional valence/arousal to dynamic UI themes.
      </p>

      <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
        <div style={{ flex: 1 }}>
          <label style={{ display: 'block', color: NEURAL_COLORS.muted, fontSize: '12px', marginBottom: '6px' }}>
            Valence: {valence.toFixed(2)}
          </label>
          <input
            type="range"
            min={-1}
            max={1}
            step={0.05}
            value={valence}
            onChange={(e) => setValence(parseFloat(e.target.value))}
            style={{ width: '100%' }}
          />
        </div>
        <div style={{ flex: 1 }}>
          <label style={{ display: 'block', color: NEURAL_COLORS.muted, fontSize: '12px', marginBottom: '6px' }}>
            Arousal: {arousal.toFixed(2)}
          </label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={arousal}
            onChange={(e) => setArousal(parseFloat(e.target.value))}
            style={{ width: '100%' }}
          />
        </div>
      </div>

      <button
        onClick={map}
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
        {loading ? 'Mapping...' : 'Map Emotion'}
      </button>

      {error && (
        <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '12px' }}>
          {error}
        </div>
      )}

      {recentEmotion && (
        <div style={{ marginBottom: '12px', fontSize: '12px', color: NEURAL_COLORS.muted }}>
          Recent emotion: <strong style={{ color: NEURAL_COLORS.text }}>{recentEmotion.dominant_emotion}</strong>
        </div>
      )}

      {mapping && (
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
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Detected Emotion</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600 }}>{mapping.emotion}</div>
            </div>
            <div style={{ flex: 1, minWidth: '120px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Layout Density</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600 }}>{mapping.layout_density}</div>
            </div>
            <div style={{ flex: 1, minWidth: '120px' }}>
              <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '4px' }}>Motion Intensity</div>
              <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600 }}>{(mapping.motion_intensity * 100).toFixed(0)}%</div>
            </div>
          </div>
          <div style={{ marginBottom: '12px' }}>
            <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '6px' }}>UI Theme</div>
            <div
              style={{
                height: '40px',
                borderRadius: '8px',
                background: mapping.ui_theme.background,
                border: `1px solid ${mapping.ui_theme.primary}40`,
              }}
            />
          </div>
          <div>
            <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '6px' }}>Recommended Actions</div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {mapping.recommended_actions.map((a, i) => (
                <span
                  key={i}
                  style={{
                    background: `${NEURAL_COLORS.primary}20`,
                    border: `1px solid ${NEURAL_COLORS.primary}40`,
                    borderRadius: '999px',
                    padding: '4px 10px',
                    fontSize: '11px',
                    color: NEURAL_COLORS.accent,
                  }}
                >
                  {a}
                </span>
              ))}
            </div>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
