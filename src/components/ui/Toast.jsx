import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Icon from '../design/Iconography'

const ToastContext = createContext(null)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const idRef = useRef(0)

  const addToast = useCallback((message, options = {}) => {
    const id = ++idRef.current
    const toast = {
      id,
      message,
      type: options.type || 'info',
      duration: options.duration ?? 4000,
      action: options.action || null
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
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used within ToastProvider')
  return context
}

function ToastContainer({ toasts, onDismiss }) {
  const typeConfig = {
    success: { bg: 'rgba(52, 211, 153, 0.15)', border: '#34d399', icon: 'check', color: '#34d399' },
    error: { bg: 'rgba(239, 68, 68, 0.15)', border: '#ef4444', icon: 'x', color: '#ef4444' },
    warning: { bg: 'rgba(251, 191, 36, 0.15)', border: '#fbbf24', icon: 'alert', color: '#fbbf24' },
    info: { bg: 'rgba(6, 182, 212, 0.15)', border: '#06b6d4', icon: 'info', color: '#06b6d4' }
  }

  return (
    <div style={{
      position: 'fixed',
      top: '20px',
      right: '20px',
      zIndex: 9999,
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
      maxWidth: '400px',
      width: 'calc(100% - 40px)'
    }}>
      <AnimatePresence>
        {toasts.map(toast => {
          const config = typeConfig[toast.type] || typeConfig.info
          return (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, x: 100, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 100, scale: 0.95 }}
              transition={{ type: 'spring', damping: 20, stiffness: 300 }}
              style={{
                backgroundColor: config.bg,
                border: `1px solid ${config.border}`,
                borderRadius: '12px',
                padding: '14px 18px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
                boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
                backdropFilter: 'blur(12px)'
              }}
              role="alert"
              aria-live="assertive"
            >
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
