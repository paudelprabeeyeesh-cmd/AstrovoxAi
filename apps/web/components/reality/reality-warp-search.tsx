'use client'

import { motion } from 'framer-motion'
import { useRealityStore } from '@/lib/store/reality-store'

export function RealityWarpSearchResult({ children, className }: { children: React.ReactNode; className?: string }) {
  const warp = useRealityStore((s) => s.mode === 'warp')

  return (
    <motion.div
      className={className}
      animate={
        warp
          ? {
              rotate: [0, 0.3, -0.3, 0],
              scale: [1, 1.02, 0.98, 1],
              borderRadius: ['12px', '24px', '12px'],
            }
          : { rotate: 0, scale: 1, borderRadius: '12px' }
      }
      transition={{ duration: 4, repeat: Infinity }}
      style={{
        background: warp ? 'linear-gradient(135deg, rgba(255,0,128,0.1), rgba(0,255,255,0.1))' : undefined,
        boxShadow: warp ? '0 0 30px rgba(255,0,128,0.25)' : undefined,
      }}
    >
      {children}
    </motion.div>
  )
}
