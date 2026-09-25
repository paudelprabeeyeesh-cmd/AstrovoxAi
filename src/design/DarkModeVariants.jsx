import { useMemo } from 'react'
import { THEMES } from './DesignTokens'

const DARK_VARIANTS = {
  astrovox: {
    name: 'Astrovox Prime',
    ...THEMES.astrovox
  },
  midnight: {
    name: 'Midnight',
    colors: {
      background: '#000000',
      surface: '#0a0a0a',
      surfaceHover: '#171717',
      border: '#262626',
      borderFocus: '#3b82f6',
      text: '#fafafa',
      textMuted: '#a3a3a3',
      primary: '#3b82f6',
      primaryHover: '#60a5fa',
      secondary: '#a855f7',
      accent: '#6366f1',
      success: '#22c55e',
      warning: '#eab308',
      error: '#ef4444',
      errorBg: 'rgba(239, 68, 68, 0.1)',
      code: '#0a0a0a',
      codeText: '#fafafa'
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
  ocean: {
    name: 'Ocean Depth',
    colors: {
      background: '#0c1222',
      surface: '#111827',
      surfaceHover: '#1f2937',
      border: '#1f2937',
      borderFocus: '#06b6d4',
      text: '#f1f5f9',
      textMuted: '#94a3b8',
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
  forest: {
    name: 'Forest',
    colors: {
      background: '#0a1a0a',
      surface: '#143314',
      surfaceHover: '#1f4d1f',
      border: '#2d5a2d',
      borderFocus: '#4ade80',
      text: '#ecfdf5',
      textMuted: '#86efac',
      primary: '#4ade80',
      primaryHover: '#86efac',
      secondary: '#a3e635',
      accent: '#bef264',
      success: '#22c55e',
      warning: '#facc15',
      error: '#f87171',
      errorBg: 'rgba(248, 113, 113, 0.1)',
      code: '#052e16',
      codeText: '#ecfdf5'
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
  sunset: {
    name: 'Sunset',
    colors: {
      background: '#1a0f0a',
      surface: '#2d1f15',
      surfaceHover: '#3d2b1f',
      border: '#4a3728',
      borderFocus: '#f97316',
      text: '#fff7ed',
      textMuted: '#fdba74',
      primary: '#f97316',
      primaryHover: '#fb923c',
      secondary: '#fbbf24',
      accent: '#fcd34d',
      success: '#22c55e',
      warning: '#facc15',
      error: '#ef4444',
      errorBg: 'rgba(239, 68, 68, 0.1)',
      code: '#1c0f0a',
      codeText: '#fff7ed'
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
  }
}

export function useDarkVariants() {
  const variantNames = Object.keys(DARK_VARIANTS)
  return {
    variants: DARK_VARIANTS,
    variantNames,
    getVariant: (name) => DARK_VARIANTS[name] || DARK_VARIANTS.astrovox
  }
}

export default DARK_VARIANTS
