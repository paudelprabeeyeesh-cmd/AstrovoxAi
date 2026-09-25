import { useState, useRef, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import Icon from '../design/Iconography'

export default function StreamingMessage({ content, isComplete, onRetry, model }) {
  const [displayedContent, setDisplayedContent] = useState('')
  const [isTyping, setIsTyping] = useState(!isComplete)
  const contentRef = useRef(null)

  useEffect(() => {
    if (isComplete) {
      setDisplayedContent(content)
      setIsTyping(false)
      return
    }

    if (!content) return
    setDisplayedContent(content)
    setIsTyping(true)
  }, [content, isComplete])

  useEffect(() => {
    if (isComplete || !contentRef.current) return
    contentRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [displayedContent, isComplete])

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        padding: '12px 16px',
        backgroundColor: 'var(--astrovox-surface)',
        border: '1px solid var(--astrovox-border)',
        borderRadius: 'var(--astrovox-radius-lg)',
        maxWidth: '80%'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              backgroundColor: 'var(--astrovox-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--astrovox-bg)',
              fontSize: '12px',
              fontWeight: 'bold'
            }}
          >
            AI
          </div>
          <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--astrovox-accent)' }}>
            {model || 'Assistant'}
          </span>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {onRetry && (
            <button
              onClick={onRetry}
              style={{
                background: 'transparent',
                border: '1px solid var(--astrovox-border)',
                borderRadius: 'var(--astrovox-radius-sm)',
                padding: '4px 8px',
                color: 'var(--astrovox-text-muted)',
                cursor: 'pointer',
                fontSize: '10px',
                fontFamily: 'inherit'
              }}
              aria-label="Retry"
            >
              <Icon name="refresh" size={14} />
            </button>
          )}
        </div>
      </div>
      <div
        ref={contentRef}
        style={{
          fontSize: '13px',
          lineHeight: '1.6',
          color: 'var(--astrovox-text)',
          whiteSpace: 'pre-wrap',
          wordWrap: 'break-word'
        }}
      >
        {displayedContent}
        {isTyping && (
          <motion.span
            animate={{ opacity: [1, 0, 1] }}
            transition={{ duration: 0.8, repeat: Infinity }}
            style={{ marginLeft: '2px', color: 'var(--astrovox-primary)' }}
          >
            ▋
          </motion.span>
        )}
      </div>
      {isTyping && (
        <div style={{ display: 'flex', gap: '4px', marginTop: '4px' }}>
          <motion.div
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 1, repeat: Infinity, delay: 0 }}
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: 'var(--astrovox-primary)'
            }}
          />
          <motion.div
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 1, repeat: Infinity, delay: 0.2 }}
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: 'var(--astrovox-primary)'
            }}
          />
          <motion.div
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 1, repeat: Infinity, delay: 0.4 }}
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: 'var(--astrovox-primary)'
            }}
          />
        </div>
      )}
    </div>
  )
}
