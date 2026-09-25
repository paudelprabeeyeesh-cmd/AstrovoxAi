import React, { useState, useRef, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useReducedMotion } from '../../design/DesignTokens'

export function Tooltip({ content, children, side = 'top', delay = 300 }) {
  const [isVisible, setIsVisible] = useState(false)
  const timerRef = useRef(null)
  const reducedMotion = useReducedMotion()

  const show = useCallback(() => {
    timerRef.current = setTimeout(() => setIsVisible(true), delay)
  }, [delay])

  const hide = useCallback(() => {
    clearTimeout(timerRef.current)
    setIsVisible(false)
  }, [])

  useEffect(() => {
    return () => clearTimeout(timerRef.current)
  }, [])

  const sideStyles = {
    top: { bottom: '100%', left: '50%', transform: 'translateX(-50%)', marginBottom: '8px' },
    bottom: { top: '100%', left: '50%', transform: 'translateX(-50%)', marginTop: '8px' },
    left: { right: '100%', top: '50%', transform: 'translateY(-50%)', marginRight: '8px' },
    right: { left: '100%', top: '50%', transform: 'translateY(-50%)', marginLeft: '8px' }
  }

  return (
    <div
      style={{ position: 'relative', display: 'inline-flex' }}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}
      <AnimatePresence>
        {isVisible && content && (
          <motion.div
            initial={reducedMotion ? { opacity: 1 } : { opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={reducedMotion ? { opacity: 0 } : { opacity: 0, scale: 0.95 }}
            transition={{ duration: reducedMotion ? 0 : 0.15 }}
            style={{
              position: 'absolute',
              ...sideStyles[side],
              backgroundColor: 'var(--astrovox-surface)',
              border: '1px solid var(--astrovox-border)',
              borderRadius: '8px',
              padding: '6px 12px',
              fontSize: '12px',
              color: 'var(--astrovox-text)',
              whiteSpace: 'nowrap',
              zIndex: 9999,
              boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
              pointerEvents: 'none'
            }}
            role="tooltip"
          >
            {content}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
