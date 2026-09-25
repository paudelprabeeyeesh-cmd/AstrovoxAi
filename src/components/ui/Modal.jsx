import React, { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useFocusManagement } from './KeyboardShortcuts'
import Icon from '../design/Iconography'

export function Modal({ isOpen, onClose, title, children, width = '480px', showClose = true }) {
  const modalRef = useRef(null)
  const { trapFocus } = useFocusManagement()

  useEffect(() => {
    if (isOpen && modalRef.current) {
      const cleanup = trapFocus(modalRef.current)
      return cleanup
    }
  }, [isOpen, trapFocus])

  useEffect(() => {
    if (!isOpen) return
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }, [isOpen, onClose])

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
      return () => { document.body.style.overflow = '' }
    }
  }, [isOpen])

  return (
    <AnimatePresence>
      {isOpen && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 9998 }}>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            style={{
              position: 'absolute',
              inset: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              backdropFilter: 'blur(4px)'
            }}
            aria-hidden="true"
          />
          <div
            style={{
              position: 'relative',
              zIndex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: '100vh',
              padding: '20px'
            }}
          >
            <motion.div
              ref={modalRef}
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              role="dialog"
              aria-modal="true"
              aria-labelledby="modal-title"
              style={{
                backgroundColor: 'var(--astrovox-surface)',
                border: '1px solid var(--astrovox-border)',
                borderRadius: '16px',
                width: '100%',
                maxWidth: width,
                maxHeight: '90vh',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
                boxShadow: '0 24px 80px rgba(0,0,0,0.5)'
              }}
            >
              {title && (
                <div style={{
                  padding: '20px 24px',
                  borderBottom: '1px solid var(--astrovox-border)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}>
                  <h2 id="modal-title" style={{ margin: 0, fontSize: '16px', fontWeight: '600' }}>
                    {title}
                  </h2>
                  {showClose && (
                    <button
                      onClick={onClose}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--astrovox-text-muted)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        padding: '4px',
                        borderRadius: '6px'
                      }}
                      aria-label="Close dialog"
                    >
                      <Icon name="x" size={18} />
                    </button>
                  )}
                </div>
              )}
              <div style={{ overflowY: 'auto', padding: '24px' }}>
                {children}
              </div>
            </motion.div>
          </div>
        </div>
      )}
    </AnimatePresence>
  )
}
