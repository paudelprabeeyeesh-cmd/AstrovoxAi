'use client'

import { motion } from 'framer-motion'
import { useRealityStore } from '@/lib/store/reality-store'

export function IntangibilityMode({ children, className }: { children: React.ReactNode; className?: string }) {
  const intangibilityEnabled = useRealityStore((s) => s.intangibilityEnabled)

  return (
    <motion.div
      className={className}
      animate={{
        opacity: intangibilityEnabled ? 0.3 : 1,
        y: intangibilityEnabled ? -4 : 0,
      }}
      transition={{ duration: 0.3 }}
      style={{ pointerEvents: intangibilityEnabled ? 'none' : 'auto' }}
    >
      {children}
    </motion.div>
  )
}
