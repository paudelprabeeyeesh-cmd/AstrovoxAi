import { useState, useCallback } from 'react'

export const A11Y_SPECS = {
  WCAG_LEVEL: 'AA',
  MIN_CONTRAST_RATIO: 4.5,
  MIN_CONTRAST_RATIO_LARGE: 3,
  FOCUS_INDICATOR_WIDTH: '2px',
  FOCUS_INDICATOR_OFFSET: '2px',
  MIN_TOUCH_TARGET: 44,
  MIN_FONT_SIZE: 12,
  LINE_HEIGHT_MIN: 1.5,
  MAX_LINE_LENGTH: 80,
  ANIMATION_DURATION: 200,
  SKIP_LINK_OFFSET: 8,
  LANDMARK_ROLES: ['banner', 'navigation', 'main', 'complementary', 'contentinfo', 'search', 'form', 'dialog'],
  ARIA_LIVE_POLICIES: ['polite', 'assertive'],
  HEADING_LEVELS: [1, 2, 3, 4, 5, 6],
  COLOR_BLIND_SAFE_PALETTE: {
    primary: '#06b6d4',
    secondary: '#f472b6',
    success: '#34d399',
    warning: '#fbbf24',
    error: '#ef4444',
    info: '#67e8f9'
  },
  KEYBOARD_SHORTCUTS: {
    sendMessage: { keys: ['Enter'], ctrl: false, shift: false, description: 'Send message' },
    newMessage: { keys: ['n'], ctrl: true, shift: false, description: 'New conversation' },
    search: { keys: ['k'], ctrl: true, shift: false, description: 'Search conversations' },
    toggleTheme: { keys: ['t'], ctrl: true, shift: false, description: 'Toggle theme' },
    focusInput: { keys: ['i'], ctrl: true, shift: false, description: 'Focus message input' },
    help: { keys: ['?'], ctrl: false, shift: false, description: 'Show keyboard shortcuts' },
    escape: { keys: ['Escape'], ctrl: false, shift: false, description: 'Close dialog / Cancel' }
  }
}

export function useAccessibility() {
  const [announcements, setAnnouncements] = useState([])

  const announce = useCallback((message, priority = 'polite') => {
    const id = crypto.randomUUID()
    setAnnouncements(prev => [...prev, { id, message, priority, timestamp: Date.now() }])
    setTimeout(() => {
      setAnnouncements(prev => prev.filter(a => a.id !== id))
    }, 1000)
  }, [])

  return { announcements, announce, specs: A11Y_SPECS }
}

export default A11Y_SPECS
