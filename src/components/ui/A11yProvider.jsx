import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { A11Y_SPECS } from '../../design/AccessibilitySpecs'
import { useFocusManagement } from './KeyboardShortcuts'

const A11yContext = createContext(null)

export function A11yProvider({ children, announce }) {
  const [screenReaderMode, setScreenReaderMode] = useState(false)
  const [highContrastMode, setHighContrastMode] = useState(false)
  const [reducedMotion, setReducedMotion] = useState(false)
  const [focusVisible, setFocusVisible] = useState(false)
  const { focusFirstInteractive, trapFocus } = useFocusManagement()

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
    announce: announce || (() => {}),
    specs: A11Y_SPECS
  }

  return <A11yContext.Provider value={value}>{children}</A11yContext.Provider>
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
