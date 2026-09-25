import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { getCompletionSuggestions, recordCompletion } from '../../services/predictionService'

export default function PredictiveText({ onSelectSuggestion, interface = 'universal' }) {
  const [prefix, setPrefix] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [activeIndex, setActiveIndex] = useState(-1)

  useEffect(() => {
    if (!prefix.trim()) {
      setSuggestions([])
      return
    }
    const timer = setTimeout(async () => {
      try {
        const data = await getCompletionSuggestions(prefix, null, interface, 8)
        setSuggestions(data.suggestions || [])
        setActiveIndex(-1)
      } catch (e) {
        console.error('Completion failed:', e)
      }
    }, 150)
    return () => clearTimeout(timer)
  }, [prefix, interface])

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex(prev => Math.min(prev + 1, suggestions.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex(prev => Math.max(prev - 1, -1))
    } else if (e.key === 'Tab' && activeIndex >= 0) {
      e.preventDefault()
      const selected = suggestions[activeIndex]
      setPrefix(selected.text)
      onSelectSuggestion?.(selected)
      recordCompletion(prefix, selected.text, interface)
      setSuggestions([])
    }
  }, [suggestions, activeIndex, prefix, interface, onSelectSuggestion])

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '8px 12px',
        backgroundColor: 'var(--astrovox-bg)',
        border: '1px solid var(--astrovox-border)',
        borderRadius: 'var(--astrovox-radius-md)',
      }}>
        <span style={{ color: '#06b6d4', fontSize: '14px' }}>🔮</span>
        <input
          type="text"
          value={prefix}
          onChange={(e) => setPrefix(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Start typing for predictions..."
          aria-label="Predictive text"
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            color: 'var(--astrovox-text)',
            fontSize: '13px',
            outline: 'none',
            fontFamily: 'inherit'
          }}
        />
        <span style={{ fontSize: '10px', color: '#64748b' }}>Tab to accept</span>
      </div>

      {suggestions.length > 0 && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          marginTop: '4px',
          backgroundColor: 'var(--astrovox-bg)',
          border: '1px solid var(--astrovox-border)',
          borderRadius: 'var(--astrovox-radius-md)',
          maxHeight: '200px',
          overflow: 'auto',
          zIndex: 1000
        }}>
          {suggestions.map((s, idx) => (
            <motion.div
              key={s.suggestion_id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              onClick={() => {
                setPrefix(s.text)
                onSelectSuggestion?.(s)
                recordCompletion(prefix, s.text, interface)
                setSuggestions([])
              }}
              style={{
                padding: '8px 12px',
                cursor: 'pointer',
                fontSize: '12px',
                color: idx === activeIndex ? '#f59e0b' : 'var(--astrovox-text)',
                backgroundColor: idx === activeIndex ? 'rgba(245,158,11,0.1)' : 'transparent',
                borderBottom: '1px solid var(--astrovox-border)',
                display: 'flex',
                justifyContent: 'space-between'
              }}
            >
              <span>{s.text}</span>
              <span style={{ fontSize: '10px', color: '#64748b' }}>
                {(s.confidence * 100).toFixed(0)}%
              </span>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
