'use client'

import { motion } from 'framer-motion'
import { useRealityStore } from '@/lib/store/reality-store'

export function DimensionalRift({ children, className }: { children: React.ReactNode; className?: string }) {
  const riftIntensity = useRealityStore((s) => s.riftIntensity)
  const intensity = Math.min(Math.max(riftIntensity, 0), 1)

  return (
    <motion.div
      className={className}
      style={{
        background: intensity > 0 ? 'linear-gradient(135deg, rgba(120,0,255,0.15), rgba(0,200,255,0.15))' : undefined,
        boxShadow: intensity > 0 ? `0 0 ${20 * intensity}px rgba(120,0,255,${0.4 * intensity})` : undefined,
        borderRadius: intensity > 0 ? `${12 + intensity * 40}px` : undefined,
      }}
      animate={
        intensity > 0
          ? {
              rotate: [0, 0.5, -0.5, 0],
              scale: [1, 1.02, 0.98, 1],
            }
          : { rotate: 0, scale: 1 }
      }
      transition={{ duration: 3 / (intensity || 1), repeat: Infinity }}
    >
      {children}
    </motion.div>
  )
}
