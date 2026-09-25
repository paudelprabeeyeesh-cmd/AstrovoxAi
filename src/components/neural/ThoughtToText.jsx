import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { thoughtToText, getRecentEpochs } from '../../services/neuralService'

const NEURAL_COLORS = {
  primary: '#06b6d4',
  secondary: '#8b5cf6',
  accent: '#22d3ee',
  background: 'rgba(6, 182, 212, 0.05)',
  cardBackground: 'rgba(6, 182, 212, 0.08)',
  border: 'rgba(6, 182, 212, 0.25)',
  text: '#e5e7eb',
  muted: '#9ca3af',
}

export function ThoughtToText({ className = '', style = {} }) {
  const [embedding, setEmbedding] = useState('')
  const [topK, setTopK] = useState(1)
  const [texts, setTexts] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleGenerate = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const parsed = embedding
        .split(',')
        .map((s) => parseFloat(s.trim()))
        .filter((n) => !isNaN(n))
      const res = await thoughtToText(parsed.length > 0 ? parsed : [0.1, 0.2, 0.3], topK)
      setTexts(res.texts || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [embedding, topK])

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
        Thought-to-Text Decoder
      </h3>
      <p style={{ margin: '0 0 16px 0', color: NEURAL_COLORS.muted, fontSize: '13px' }}>
        Convert neural embeddings into textual representations.
      </p>

      <div style={{ marginBottom: '12px' }}>
        <label style={{ display: 'block', color: NEURAL_COLORS.muted, fontSize: '12px', marginBottom: '6px' }}>
          Neural Embedding (comma-separated floats)
        </label>
        <textarea
          value={embedding}
          onChange={(e) => setEmbedding(e.target.value)}
          placeholder="0.1, 0.2, 0.3, ..."
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

      <div style={{ marginBottom: '16px', display: 'flex', gap: '12px', alignItems: 'center' }}>
        <label style={{ color: NEURAL_COLORS.muted, fontSize: '12px' }}>Top-K</label>
        <input
          type="number"
          min={1}
          max={10}
          value={topK}
          onChange={(e) => setTopK(parseInt(e.target.value || '1', 10))}
          style={{
            width: '64px',
            background: 'rgba(0,0,0,0.3)',
            border: `1px solid ${NEURAL_COLORS.border}`,
            borderRadius: '8px',
            padding: '8px',
            color: NEURAL_COLORS.text,
            fontSize: '13px',
          }}
        />
        <button
          onClick={handleGenerate}
          disabled={loading}
          style={{
            marginLeft: 'auto',
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
          {loading ? 'Decoding...' : 'Decode Thought'}
        </button>
      </div>

      {error && (
        <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '12px' }}>
          {error}
        </div>
      )}

      {texts.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {texts.map((text, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              style={{
                background: 'rgba(0,0,0,0.25)',
                border: `1px solid ${NEURAL_COLORS.border}`,
                borderRadius: '8px',
                padding: '10px 12px',
                color: NEURAL_COLORS.text,
                fontSize: '13px',
                fontFamily: 'monospace',
              }}
            >
              {text}
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  )
}
