import { useEffect, useCallback } from 'react'
import { A11Y_SPECS } from '../../design/AccessibilitySpecs'

export function useKeyboardShortcuts(shortcuts = {}) {
  const handleKeyDown = useCallback((event) => {
    const allShortcuts = { ...A11Y_SPECS.KEYBOARD_SHORTCUTS, ...shortcuts }
    for (const [name, shortcut] of Object.entries(allShortcuts)) {
      const keysMatch = shortcut.keys.every(key => {
        if (key === 'Enter') return event.key === 'Enter'
        if (key === 'Escape') return event.key === 'Escape'
        return event.key.toLowerCase() === key.toLowerCase()
      })
      const modifiersMatch = (!shortcut.ctrl || event.ctrlKey || event.metaKey) &&
                            (!shortcut.shift || event.shiftKey) &&
                            (!shortcut.alt || event.altKey)

      if (keysMatch && modifiersMatch) {
        event.preventDefault()
        event.stopPropagation()
        if (shortcut.handler) shortcut.handler(event)
        return true
      }
    }
    return false
  }, [shortcuts])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
}

export function useFocusManagement() {
  const focusFirstInteractive = useCallback((container) => {
    if (!container) return
    const focusable = container.querySelectorAll(
      'button, [href], input, textarea, select, details, [tabindex]:not([tabindex="-1"])'
    )
    if (focusable.length > 0) {
      focusable[0].focus()
    }
  }, [])

  const trapFocus = useCallback((container) => {
    if (!container) return () => {}
    const focusable = container.querySelectorAll(
      'button, [href], input, textarea, select, details, [tabindex]:not([tabindex="-1"])'
    )
    if (focusable.length === 0) return () => {}

    const first = focusable[0]
    const last = focusable[focusable.length - 1]

    const handleTab = (e) => {
      if (e.key !== 'Tab') return
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault()
          last.focus()
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }

    container.addEventListener('keydown', handleTab)
    return () => container.removeEventListener('keydown', handleTab)
  }, [])

  return { focusFirstInteractive, trapFocus }
}
