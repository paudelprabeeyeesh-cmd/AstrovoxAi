import { THEMES, useTheme } from '../design/DesignTokens'

export function ThemeEngine({ children }) {
  const { theme, themeName, setTheme } = useTheme()

  const themeStyles = {
    '--astrovox-bg': theme.colors.background,
    '--astrovox-surface': theme.colors.surface,
    '--astrovox-surface-hover': theme.colors.surfaceHover,
    '--astrovox-border': theme.colors.border,
    '--astrovox-border-focus': theme.colors.borderFocus,
    '--astrovox-text': theme.colors.text,
    '--astrovox-text-muted': theme.colors.textMuted,
    '--astrovox-primary': theme.colors.primary,
    '--astrovox-primary-hover': theme.colors.primaryHover,
    '--astrovox-secondary': theme.colors.secondary,
    '--astrovox-accent': theme.colors.accent,
    '--astrovox-success': theme.colors.success,
    '--astrovox-warning': theme.colors.warning,
    '--astrovox-error': theme.colors.error,
    '--astrovox-error-bg': theme.colors.errorBg,
    '--astrovox-code': theme.colors.code,
    '--astrovox-code-text': theme.colors.codeText,
    '--astrovox-font-sans': theme.fonts.sans,
    '--astrovox-font-mono': theme.fonts.mono,
    '--astrovox-radius-sm': theme.radius.sm,
    '--astrovox-radius-md': theme.radius.md,
    '--astrovox-radius-lg': theme.radius.lg,
    '--astrovox-radius-xl': theme.radius.xl,
    '--astrovox-radius-full': theme.radius.full
  }

  return (
    <div
      style={{
        ...themeStyles,
        backgroundColor: theme.colors.background,
        color: theme.colors.text,
        fontFamily: theme.fonts.sans,
        minHeight: '100vh',
        transition: 'background-color 0.3s ease, color 0.3s ease'
      }}
      data-theme={themeName}
    >
      <div
        style={{
          position: 'absolute',
          width: 1,
          height: 1,
          padding: 0,
          margin: -1,
          overflow: 'hidden',
          clip: 'rect(0, 0, 0, 0)',
          whiteSpace: 'nowrap',
          border: 0
        }}
        aria-live="polite"
        aria-atomic="true"
      />
      {children}
      <ThemeSwitcher currentTheme={themeName} onThemeChange={setTheme} themes={Object.keys(THEMES)} />
    </div>
  )
}

function ThemeSwitcher({ currentTheme, onThemeChange, themes }) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        zIndex: 1000
      }}
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: '44px',
          height: '44px',
          borderRadius: '50%',
          backgroundColor: 'var(--astrovox-primary)',
          color: 'var(--astrovox-bg)',
          border: 'none',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
        }}
        aria-label="Toggle theme"
        aria-expanded={isOpen}
      >
        <Icon name="palette" size={20} />
      </button>
      {isOpen && (
        <div
          style={{
            position: 'absolute',
            bottom: '56px',
            right: 0,
            backgroundColor: 'var(--astrovox-surface)',
            border: '1px solid var(--astrovox-border)',
            borderRadius: 'var(--astrovox-radius-lg)',
            padding: '8px',
            minWidth: '180px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.3)'
          }}
          role="menu"
        >
          {themes.map(theme => (
            <button
              key={theme}
              onClick={() => { onThemeChange(theme); setIsOpen(false) }}
              style={{
                display: 'block',
                width: '100%',
                padding: '8px 12px',
                backgroundColor: currentTheme === theme ? 'var(--astrovix-primary)' : 'transparent',
                color: 'var(--astrovox-text)',
                border: 'none',
                borderRadius: 'var(--astrovox-radius-sm)',
                cursor: 'pointer',
                textAlign: 'left',
                fontSize: '13px',
                fontFamily: 'inherit'
              }}
              role="menuitem"
              aria-current={currentTheme === theme ? 'true' : undefined}
            >
              {THEMES[theme]?.name || theme}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

import { useState } from 'react'
import Icon from '../design/Iconography'
