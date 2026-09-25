import React, { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { THEMES, useTheme } from '../../design/DesignTokens.js'
import Icon from '../design/Iconography.jsx'

export function ThemeSwitcher({ currentTheme, onThemeChange, themes }) {
  const [isOpen, setIsOpen] = useState(false)
  const [previewTheme, setPreviewTheme] = useState(null)

  const handleThemeSelect = useCallback((theme) => {
    onThemeChange(theme)
    setPreviewTheme(null)
    setIsOpen(false)
  }, [onThemeChange])

  const handleThemeHover = useCallback((theme) => {
    setPreviewTheme(theme)
  }, [])

  const handleThemeLeave = useCallback(() => {
    setPreviewTheme(null)
  }, [])

  const activeTheme = previewTheme || currentTheme
  const theme = THEMES[activeTheme] || THEMES.astrovox

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
            minWidth: '220px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
            zIndex: 1001
          }}
          role="menu"
        >
          {themes.map(themeKey => (
            <button
              key={themeKey}
              onClick={() => handleThemeSelect(themeKey)}
              onMouseEnter={() => handleThemeHover(themeKey)}
              onMouseLeave={handleThemeLeave}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                width: '100%',
                padding: '10px 12px',
                 backgroundColor: currentTheme === themeKey ? 'var(--astrovox-primary)' : 'transparent',
                color: 'var(--astrovox-text)',
                border: 'none',
                borderRadius: 'var(--astrovox-radius-sm)',
                cursor: 'pointer',
                textAlign: 'left',
                fontSize: '13px',
                fontFamily: 'inherit',
                transition: 'background-color 0.15s'
              }}
              role="menuitem"
              aria-current={currentTheme === themeKey ? 'true' : undefined}
            >
              <div style={{
                width: '16px',
                height: '16px',
                borderRadius: '4px',
                backgroundColor: THEMES[themeKey]?.colors?.primary || '#06b6d4',
                border: '1px solid var(--astrovox-border)',
                flexShrink: 0
              }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: currentTheme === themeKey ? '600' : '400' }}>
                  {THEMES[themeKey]?.name || themeKey}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', marginTop: '2px' }}>
                  {getThemeDescription(themeKey)}
                </div>
              </div>
              {currentTheme === themeKey && (
                <Icon name="check" size={14} color="var(--astrovox-primary)" />
              )}
            </button>
          ))}
        </div>
      )}
      <AnimatePresence>
        {previewTheme && previewTheme !== currentTheme && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            style={{
              position: 'absolute',
              bottom: '56px',
              right: '230px',
              backgroundColor: theme.colors.background,
              border: `1px solid ${theme.colors.border}`,
              borderRadius: '12px',
              padding: '16px',
              width: '200px',
              boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
              zIndex: 1000,
              pointerEvents: 'none'
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: '600', marginBottom: '8px', color: theme.colors.text }}>
              Preview: {THEMES[previewTheme]?.name || previewTheme}
            </div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {Object.entries(theme.colors).slice(0, 6).map(([key, color]) => (
                <div
                  key={key}
                  style={{
                    width: '24px',
                    height: '24px',
                    borderRadius: '4px',
                    backgroundColor: color,
                    border: '1px solid rgba(255,255,255,0.1)'
                  }}
                  title={key}
                />
              ))}
            </div>
            <div style={{
              marginTop: '10px',
              padding: '8px',
              backgroundColor: theme.colors.surface,
              borderRadius: '6px',
              fontSize: '11px',
              color: theme.colors.textMuted
            }}>
              Live preview of theme colors
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function getThemeDescription(key) {
  const descriptions = {
    astrovox: 'Dark cyberpunk theme',
    light: 'Clean light theme',
    highContrast: 'Maximum accessibility'
  }
  return descriptions[key] || ''
}
