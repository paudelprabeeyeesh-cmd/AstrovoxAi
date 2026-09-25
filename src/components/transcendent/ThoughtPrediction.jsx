import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { predictThought } from '../../services/predictionService'

export default function ThoughtPrediction({ userId }) {
  const [predictions, setPredictions] = useState([])
  const [context, setContext] = useState({ recent_actions: [], current_state: {} })

  useEffect(() => {
    if (!userId) return
    const interval = setInterval(async () => {
      try {
        const data = await predictThought(userId, context)
        if (data.predictions && data.predictions.length > 0) {
          setPredictions(prev => [...data.predictions.slice(0, 3), ...prev].slice(0, 10))
        }
      } catch (e) {
        console.error('Thought prediction failed:', e)
      }
    }, 5000)
    return () => clearInterval(interval)
  }, [userId, context])

  if (predictions.length === 0) return null

  return (
    <div style={{
      position: 'fixed',
      bottom: '16px',
      left: '16px',
      zIndex: 9999,
      backgroundColor: 'rgba(4, 8, 20, 0.9)',
      border: '1px solid #06b6d4',
      borderRadius: '12px',
      padding: '12px 16px',
      maxWidth: '320px',
      backdropFilter: 'blur(12px)',
      boxShadow: '0 8px 32px rgba(0,0,0,0.4)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <span style={{ fontSize: '14px', color: '#06b6d4' }}>🧠</span>
        <span style={{ fontSize: '11px', color: '#06b6d4', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px' }}>
          Thought Prediction
        </span>
      </div>
      <AnimatePresence>
        {predictions.map((pred, idx) => (
          <motion.div
            key={pred.prediction_id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            style={{
              padding: '6px 8px',
              backgroundColor: 'rgba(6,182,212,0.05)',
              borderRadius: '6px',
              marginBottom: '4px',
              fontSize: '11px',
              color: '#94a3b8'
            }}
          >
            <div style={{ fontSize: '12px', color: '#e2e8f0', marginBottom: '2px' }}>
              {pred.thought_content}
            </div>
            <div style={{ fontSize: '10px', color: '#64748b' }}>
              Confidence: {(pred.confidence * 100).toFixed(0)}%
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
