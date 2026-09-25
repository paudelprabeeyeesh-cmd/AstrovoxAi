'use client'

import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { useRealityStore } from '@/lib/store/reality-store'

const GLITCH_CHARS = '!@#$%^&*()_+-=[]{}|;:,.<>?/~`░▒▓█▀▄'

function randomChar() {
  return GLITCH_CHARS[Math.floor(Math.random() * GLITCH_CHARS.length)]
}

export function RealityGlitch({ children, intensity = 0.5 }: { children: React.ReactNode; intensity?: number }) {
  const glitchIntensity = useRealityStore((s) => s.glitchIntensity)
  const active = intensity > 0 && glitchIntensity > 0

  const glitchText = useMemo(() => {
    if (!active) return ''
    return children
      ?.toString()
      .split('')
      .map((c) => (Math.random() < glitchIntensity ? randomChar() : c))
      .join('') || ''
  }, [active, children, glitchIntensity])

  return (
    <motion.span
      className="relative inline-block"
      animate={
        active
          ? {
              x: [0, -2, 2, -1, 1, 0],
              textShadow: [
                '2px 0 rgba(255,0,0,0.8), -2px 0 rgba(0,255,255,0.8)',
                '-2px 0 rgba(255,0,0,0.8), 2px 0 rgba(0,255,255,0.8)',
                '2px 0 rgba(255,0,0,0.8), -2px 0 rgba(0,255,255,0.8)',
                'none',
              ],
            }
          : { x: 0, textShadow: 'none' }
      }
      transition={{ duration: 0.2, repeat: Infinity, repeatType: 'mirror' }}
    >
      <span aria-hidden={active}>{glitchText || children}</span>
      {active && <span className="sr-only">{children}</span>}
    </motion.span>
  )
}
