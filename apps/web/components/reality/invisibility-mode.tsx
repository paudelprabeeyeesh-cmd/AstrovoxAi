'use client'

import { motion } from 'framer-motion'
import { useRealityStore } from '@/lib/store/reality-store'

export function InvisibilityMode({ children, className }: { children: React.ReactNode; className?: string }) {
  const invisibilityEnabled = useRealityStore((s) => s.invisibilityEnabled)

  return (
    <motion.div
      className={className}
      animate={{
        opacity: invisibilityEnabled ? 0.15 : 1,
        filter: invisibilityEnabled ? 'blur(6px)' : 'blur(0px)',
      }}
      transition={{ duration: 0.4 }}
    >
      {children}
    </motion.div>
  )
}
