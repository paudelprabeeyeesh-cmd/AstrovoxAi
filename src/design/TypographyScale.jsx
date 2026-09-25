export const TYPOGRAPHY = {
  scale: {
    xs: { fontSize: '10px', lineHeight: '14px', letterSpacing: '0.5px' },
    sm: { fontSize: '11px', lineHeight: '16px', letterSpacing: '0.3px' },
    base: { fontSize: '13px', lineHeight: '20px', letterSpacing: '0px' },
    md: { fontSize: '14px', lineHeight: '22px', letterSpacing: '0px' },
    lg: { fontSize: '18px', lineHeight: '28px', letterSpacing: '-0.2px' },
    xl: { fontSize: '20px', lineHeight: '32px', letterSpacing: '-0.3px' },
    '2xl': { fontSize: '24px', lineHeight: '36px', letterSpacing: '-0.4px' },
    '3xl': { fontSize: '30px', lineHeight: '44px', letterSpacing: '-0.5px' },
    '4xl': { fontSize: '36px', lineHeight: '52px', letterSpacing: '-0.6px' }
  },
  weights: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
    black: '900'
  },
  families: {
    sans: "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif",
    mono: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', 'SF Mono', monospace",
    display: "'Space Grotesk', 'Inter', system-ui, sans-serif"
  }
}

export function useTypography() {
  return {
    ...TYPOGRAPHY,
    text: (size = 'base', weight = 'normal') => ({
      fontSize: TYPOGRAPHY.scale[size]?.fontSize || TYPOGRAPHY.scale.base.fontSize,
      lineHeight: TYPOGRAPHY.scale[size]?.lineHeight || TYPOGRAPHY.scale.base.lineHeight,
      fontWeight: TYPOGRAPHY.weights[weight] || TYPOGRAPHY.weights.normal,
      fontFamily: TYPOGRAPHY.families.sans
    }),
    mono: (size = 'base') => ({
      fontSize: TYPOGRAPHY.scale[size]?.fontSize || TYPOGRAPHY.scale.base.fontSize,
      lineHeight: TYPOGRAPHY.scale[size]?.lineHeight || TYPOGRAPHY.scale.base.lineHeight,
      fontWeight: TYPOGRAPHY.weights.normal,
      fontFamily: TYPOGRAPHY.families.mono
    })
  }
}
