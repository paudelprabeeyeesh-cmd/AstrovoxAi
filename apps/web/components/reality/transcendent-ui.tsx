'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useRealityStore } from '@/lib/store/reality-store'

const PARTICLES = Array.from({ length: 40 }, (_, i) => ({
  id: i,
  x: Math.random() * 100,
  y: Math.random() * 100,
  size: Math.random() * 3 + 1,
  duration: Math.random() * 4 + 3,
}))

export function TranscendentUI({ children, className }: { children: React.ReactNode; className?: string }) {
  const transcendentEnabled = useRealityStore((s) => s.transcendentEnabled)

  return (
    <div className={className} style={{ position: 'relative' }}>
      {children}
      <AnimatePresence>
        {transcendentEnabled && (
          <motion.div
            className="pointer-events-none absolute inset-0 overflow-hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            {PARTICLES.map((p) => (
              <motion.span
                key={p.id}
                className="absolute rounded-full bg-white"
                style={{ left: `${p.x}%`, top: `${p.y}%`, width: p.size, height: p.size }}
                animate={{ y: [0, -20, 0], opacity: [0.2, 0.9, 0.2] }}
                transition={{ duration: p.duration, repeat: Infinity, ease: 'easeInOut' }}
              />
            ))}
            <motion.div
              className="absolute inset-0 bg-gradient-to-br from-purple-500/20 via-transparent to-cyan-500/20"
              animate={{ opacity: [0.3, 0.7, 0.3] }}
              transition={{ duration: 5, repeat: Infinity }}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
