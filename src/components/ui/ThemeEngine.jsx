import { THEMES, useTheme } from '../design/DesignTokens.js'
import { ThemeSwitcher } from './ThemeSwitcher'

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

