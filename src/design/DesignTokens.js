import { useState, useCallback } from 'react'

export const THEMES = {
  astrovox: {
    name: 'Astrovox Prime',
    colors: {
      background: '#02040a',
      surface: '#0f172a',
      surfaceHover: '#1e293b',
      border: '#1e293b',
      borderFocus: '#06b6d4',
      text: '#e2e8f0',
      textMuted: '#64748b',
      primary: '#06b6d4',
      primaryHover: '#22d3ee',
      secondary: '#f472b6',
      accent: '#67e8f9',
      success: '#34d399',
      warning: '#fbbf24',
      error: '#ef4444',
      errorBg: 'rgba(239, 68, 68, 0.1)',
      code: '#020617',
      codeText: '#e2e8f0'
    },
    fonts: {
      sans: "'Inter', 'Segoe UI', system-ui, sans-serif",
      mono: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace"
    },
    radius: {
      sm: '6px',
      md: '8px',
      lg: '12px',
      xl: '16px',
      full: '9999px'
    }
  },
  light: {
    name: 'Light',
    colors: {
      background: '#ffffff',
      surface: '#f8fafc',
      surfaceHover: '#f1f5f9',
      border: '#e2e8f0',
      borderFocus: '#0891b2',
      text: '#0f172a',
      textMuted: '#64748b',
      primary: '#0891b2',
      primaryHover: '#06b6d4',
      secondary: '#db2777',
      accent: '#06b6d4',
      success: '#059669',
      warning: '#d97706',
      error: '#dc2626',
      errorBg: 'rgba(220, 38, 38, 0.1)',
      code: '#f8fafc',
      codeText: '#0f172a'
    },
    fonts: {
      sans: "'Inter', 'Segoe UI', system-ui, sans-serif",
      mono: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace"
    },
    radius: {
      sm: '6px',
      md: '8px',
      lg: '12px',
      xl: '16px',
      full: '9999px'
    }
  },
  highContrast: {
    name: 'High Contrast',
    colors: {
      background: '#000000',
      surface: '#000000',
      surfaceHover: '#1a1a1a',
      border: '#ffffff',
      borderFocus: '#ffff00',
      text: '#ffffff',
      textMuted: '#ffffff',
      primary: '#ffff00',
      primaryHover: '#ffffff',
      secondary: '#ff00ff',
      accent: '#00ffff',
      success: '#00ff00',
      warning: '#ffff00',
      error: '#ff0000',
      errorBg: 'rgba(255, 0, 0, 0.2)',
      code: '#000000',
      codeText: '#ffffff'
    },
    fonts: {
      sans: "'Inter', 'Segoe UI', system-ui, sans-serif",
      mono: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace"
    },
    radius: {
      sm: '0px',
      md: '0px',
      lg: '0px',
      xl: '0px',
      full: '0px'
    }
  }
}

export function useTheme() {
  const [themeName, setThemeName] = useState(() => {
    return localStorage.getItem('astrovox-theme') || 'astrovox'
  })

  const theme = THEMES[themeName] || THEMES.astrovox

  const setTheme = useCallback((name) => {
    if (THEMES[name]) {
      setThemeName(name)
      localStorage.setItem('astrovox-theme', name)
    }
  }, [])

  return { theme, themeName, setTheme }
}
