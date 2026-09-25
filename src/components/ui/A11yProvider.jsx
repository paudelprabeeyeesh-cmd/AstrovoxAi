import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import { A11Y_SPECS } from '../../design/AccessibilitySpecs'
import { useFocusManagement } from './KeyboardShortcuts'

const A11yContext = createContext(null)

export function A11yProvider({ children }) {
  const [screenReaderMode, setScreenReaderMode] = useState(false)
  const [highContrastMode, setHighContrastMode] = useState(false)
  const [reducedMotion, setReducedMotion] = useState(false)
  const [focusVisible, setFocusVisible] = useState(false)
  const [announcements, setAnnouncements] = useState([])
  const { focusFirstInteractive, trapFocus } = useFocusManagement()
  const announcerRef = useRef(null)
  const idRef = useRef(0)

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    setReducedMotion(mediaQuery.matches)
    const handler = (e) => setReducedMotion(e.matches)
    mediaQuery.addEventListener('change', handler)
    return () => mediaQuery.removeEventListener('change', handler)
  }, [])

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-contrast: high)')
    setHighContrastMode(mediaQuery.matches)
    const handler = (e) => setHighContrastMode(e.matches)
    mediaQuery.addEventListener('change', handler)
    return () => mediaQuery.removeEventListener('change', handler)
  }, [])

  const announce = useCallback((message, priority = 'polite') => {
    const id = ++idRef.current
    setAnnouncements(prev => [...prev, { id, message, priority, timestamp: Date.now() }])

    if (announcerRef.current) {
      announcerRef.current.textContent = ''
      requestAnimationFrame(() => {
        if (announcerRef.current) {
          announcerRef.current.textContent = message
        }
      })
    }

    setTimeout(() => {
      setAnnouncements(prev => prev.filter(a => a.id !== id))
    }, 1000)
  }, [])

  const value = {
    screenReaderMode,
    setScreenReaderMode,
    highContrastMode,
    setHighContrastMode,
    reducedMotion,
    focusVisible,
    setFocusVisible,
    focusFirstInteractive,
    trapFocus,
    announce,
    specs: A11Y_SPECS
  }

  return (
    <A11yContext.Provider value={value}>
      {children}
      <div
        ref={announcerRef}
        style={{
          position: 'absolute',
          width: '1px',
          height: '1px',
          padding: 0,
          margin: '-1px',
          overflow: 'hidden',
          clip: 'rect(0, 0, 0, 0)',
          whiteSpace: 'nowrap',
          border: 0
        }}
        aria-live="polite"
        aria-atomic="true"
        role="status"
      />
      <div
        style={{
          position: 'absolute',
          width: '1px',
          height: '1px',
          padding: 0,
          margin: '-1px',
          overflow: 'hidden',
          clip: 'rect(0, 0, 0, 0)',
          whiteSpace: 'nowrap',
          border: 0
        }}
        aria-live="assertive"
        aria-atomic="true"
        role="alert"
      />
    </A11yContext.Provider>
  )
}

export function useA11y() {
  const context = useContext(A11yContext)
  if (!context) throw new Error('useA11y must be used within A11yProvider')
  return context
}

export function SkipLink({ targetId, children }) {
  return (
    <a
      href={`#${targetId}`}
      style={{
        position: 'absolute',
        top: '-40px',
        left: 0,
        backgroundColor: 'var(--astrovox-primary)',
        color: 'var(--astrovox-bg)',
        padding: '8px 16px',
        zIndex: 10000,
        transition: 'top 0.2s',
        textDecoration: 'none',
        fontWeight: '600'
      }}
      onFocus={(e) => { e.target.style.top = '0' }}
      onBlur={(e) => { e.target.style.top = '-40px' }}
    >
      {children}
    </a>
  )
}
