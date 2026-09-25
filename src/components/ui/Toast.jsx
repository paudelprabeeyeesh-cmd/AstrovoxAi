import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useReducedMotion } from '../../design/DesignTokens.js'
import Icon from '../design/Iconography.jsx'

const ToastContext = createContext(null)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const idRef = useRef(0)
  const reducedMotion = useReducedMotion()

  const addToast = useCallback((message, options = {}) => {
    const id = ++idRef.current
    const toast = {
      id,
      message,
      type: options.type || 'info',
      duration: options.duration ?? 4000,
      action: options.action || null,
      createdAt: Date.now()
    }
    setToasts(prev => [...prev, toast])
    return id
  }, [])

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={removeToast} reducedMotion={reducedMotion} />
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used within ToastProvider')
  return context
}

function ToastContainer({ toasts, onDismiss, reducedMotion }) {
  const typeConfig = {
    success: { bg: 'rgba(52, 211, 153, 0.15)', border: '#34d399', icon: 'check', color: '#34d399' },
    error: { bg: 'rgba(239, 68, 68, 0.15)', border: '#ef4444', icon: 'x', color: '#ef4444' },
    warning: { bg: 'rgba(251, 191, 36, 0.15)', border: '#fbbf24', icon: 'alert', color: '#fbbf24' },
    info: { bg: 'rgba(6, 182, 212, 0.15)', border: '#06b6d4', icon: 'info', color: '#06b6d4' }
  }

  return (
    <div
      role="region"
      aria-label="Notifications"
      style={{
        position: 'fixed',
        top: '20px',
        right: '20px',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        maxWidth: '400px',
        width: 'calc(100% - 40px)'
      }}
    >
      <AnimatePresence>
        {toasts.map(toast => {
          const config = typeConfig[toast.type] || typeConfig.info
          const progress = reducedMotion ? undefined : Math.max(0, 1 - (Date.now() - toast.createdAt) / (toast.duration || 4000))
          return (
            <motion.div
              key={toast.id}
              initial={reducedMotion ? { opacity: 0 } : { opacity: 0, x: 100, scale: 0.95 }}
              animate={reducedMotion ? { opacity: 1 } : { opacity: 1, x: 0, scale: 1 }}
              exit={reducedMotion ? { opacity: 0 } : { opacity: 0, x: 100, scale: 0.95 }}
              transition={reducedMotion ? { duration: 0 } : { type: 'spring', damping: 20, stiffness: 300 }}
              style={{
                backgroundColor: config.bg,
                border: `1px solid ${config.border}`,
                borderRadius: '12px',
                padding: '14px 18px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
                boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
                backdropFilter: 'blur(12px)',
                position: 'relative',
                overflow: 'hidden'
              }}
              role="alert"
              aria-live="assertive"
            >
              {progress !== undefined && (
                <motion.div
                  style={{
                    position: 'absolute',
                    bottom: 0,
                    left: 0,
                    height: '2px',
                    backgroundColor: config.color,
                    borderRadius: '1px'
                  }}
                  initial={{ width: '100%' }}
                  animate={{ width: '0%' }}
                  transition={{ duration: (toast.duration || 4000) / 1000, ease: 'linear' }}
                />
              )}
              <div style={{
                width: '20px',
                height: '20px',
                borderRadius: '50%',
                backgroundColor: config.bg,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                marginTop: '1px'
              }}>
                <Icon name={config.icon} size={14} color={config.color} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{
                  margin: 0,
                  fontSize: '13px',
                  color: '#e2e8f0',
                  lineHeight: '1.4',
                  wordBreak: 'break-word'
                }}>
                  {toast.message}
                </p>
              </div>
              <button
                onClick={() => onDismiss(toast.id)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#64748b',
                  cursor: 'pointer',
                  padding: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0
                }}
                aria-label="Dismiss notification"
              >
                <Icon name="x" size={16} />
              </button>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
