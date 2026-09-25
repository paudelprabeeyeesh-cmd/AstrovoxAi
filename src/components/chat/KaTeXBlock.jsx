import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function KaTeXBlock({ content, display = false }) {
  const containerRef = useRef(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    const renderMath = async () => {
      try {
        if (typeof window !== 'undefined' && window.katex) {
          if (containerRef.current) {
            window.katex.render(content, containerRef.current, {
              displayMode: display,
              throwOnError: true,
              output: 'html'
            })
          }
        }
      } catch (err) {
        setError(err.message)
      }
    }
    renderMath()
  }, [content, display])

  if (error) {
    return (
      <div
        style={{
          padding: '12px',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid var(--astrovox-error)',
          borderRadius: 'var(--astrovox-radius-md)',
          fontSize: '12px',
          color: 'var(--astrovox-error)'
        }}
      >
        <Icon name="alert" size={14} style={{ marginRight: '6px' }} />
        Math render error: {error}
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      style={{
        padding: display ? '16px' : '8px',
        backgroundColor: 'var(--astrovox-code)',
        border: '1px solid var(--astrovox-border)',
        borderRadius: 'var(--astrovox-radius-md)',
        overflowX: 'auto',
        textAlign: display ? 'center' : 'left'
      }}
    >
      <div
        ref={containerRef}
        style={{
          fontSize: display ? '16px' : '14px',
          color: 'var(--astrovox-text)'
        }}
      />
    </motion.div>
  )
}
